from django.core.cache import cache
from django.utils import translation
from django.utils.text import slugify
from reversion.models import Version
from courses import markupparser
import courses.models as cm
from utils.archive import get_single_archived
from utils.parsing import parse_link_url


def render_content(content, request=None, context=None, revision=None, lang_code=None, page=None):
    blocks = []
    embedded_pages = []
    instance = context["instance"]

    if lang_code is None:
        lang_code = translation.get_language()

    # Check cache
    if page is not None:
        cached_content = cache.get(
            f"{content.slug}_contents_{instance.slug}_{lang_code}_{page}"
        )
    else:
        cached_content = cache.get(f"{content.slug}_contents_{instance.slug}_{lang_code}")

    if cached_content is not None:
        return cached_content

    if revision is None:
        body = content.content
    else:
        body = get_single_archived(content, revision).content

    # Render the page
    context["content"] = content
    context["lang_code"] = lang_code
    markup_gen = markupparser.MarkupParser.parse(body, request, context, embedded_pages)
    segment = ""
    pages = []
    for chunk in markup_gen:
        if isinstance(chunk, str):
            segment += chunk
        elif isinstance(chunk, markupparser.PageBreak):
            blocks.append(("plain", segment))
            segment = ""
            pages.append(blocks)
            blocks = []
        else:
            blocks.append(("plain", segment))
            blocks.append(chunk)
            segment = ""

    if segment:
        blocks.append(("plain", segment))

    pages.append(blocks)

    if len(pages) > 1:
        for i, blocks in enumerate(pages, start=1):
            cache.set(
                f"{content.slug}_contents_{instance.slug}_{lang_code}_{i}",
                blocks,
                timeout=None,
            )

    full = [block for page in pages for block in page]
    cache.set(
        f"{content.slug}_contents_{instance.slug}_{lang_code}",
        full,
        timeout=None,
    )

    if page is not None:
        return pages[page - 1]
    return full




def render_terms(request, instance, context):
    lang = translation.get_language()
    termbank_contents = cache.get(f"termbank_contents_{instance.slug}_{lang}")
    term_div_data = cache.get(f"term_div_data_{instance.slug}_{lang}")

    if termbank_contents is None or term_div_data is None:
        term_context = context.copy()
        term_context["tooltip"] = True
        term_links = cm.TermToInstanceLink.objects.filter(instance__slug=instance.slug)
        term_div_data = []
        termbank_contents = {}
        terms = []
        for link in term_links:
            if link.revision is None:
                term = link.term
            else:
                term = (
                    Version.objects.get_for_object(link.term)
                    .get(revision=link.revision)
                    ._object_version.object
                )

            if term.description:
                terms.append(term)

        def sort_by_name(item):
            return item.name

        terms.sort(key=sort_by_name)
        for term in terms:
            slug = slugify(term.name, allow_unicode=True)
            description = "".join(
                markupparser.MarkupParser.parse(term.description, request, term_context)
            ).strip()
            tabs = [
                (
                    tab.title,
                    "".join(
                        markupparser.MarkupParser.parse(tab.description, request, term_context)
                    ).strip(),
                )
                for tab in term.termtab_set.all().order_by("id")
            ]
            tags = term.tags

            final_links = []
            for link in term.termlink_set.all():
                final_address, __ = parse_link_url(link.url)
                final_links.append({"url": final_address, "text": link.link_text})

            term_div_data.append(
                {
                    "slug": slug,
                    "description": description,
                    "tabs": tabs,
                    "links": final_links,
                }
            )
            term_data = {
                "slug": slug,
                "name": term.name,
                "tags": tags.values_list("name", flat=True),
                "alias": False,
            }

            def get_term_initial(term):
                try:
                    first_char = term.upper()[0]
                except IndexError:
                    first_char = "#"
                else:
                    if not first_char.isalpha():
                        first_char = "#"
                return first_char

            first_char = get_term_initial(term.name)
            if first_char in termbank_contents:
                termbank_contents[first_char].append(term_data)
            else:
                termbank_contents[first_char] = [term_data]

            aliases = cm.TermAlias.objects.filter(term=term)
            for alias in aliases:
                alias_data = {
                    "slug": slug,
                    "name": term.name,
                    "alias": alias.name,
                }
                first_char = get_term_initial(alias.name)

                if first_char in termbank_contents:
                    termbank_contents[first_char].append(alias_data)
                else:
                    termbank_contents[first_char] = [alias_data]

        cache.set(
            f"termbank_contents_{instance.slug}_{lang}",
            termbank_contents,
            timeout=None,
        )

        cache.set(
            f"term_div_data_{instance.slug}_{lang}",
            term_div_data,
            timeout=None,
        )
    return termbank_contents, term_div_data
