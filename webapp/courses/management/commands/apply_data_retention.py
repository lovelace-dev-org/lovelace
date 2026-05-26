from collections import defaultdict
from django.core.management.base import BaseCommand
from utils.data import apply_data_retention


class Command(BaseCommand):
    help = "Apply users' data retention policy and delete/anonymize records accordingly."

    def add_arguments(self, parser):
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Execute the deletions. Only use after checking once.",
        )
        parser.add_argument(
            "--silent",
            action="store_true",
            help="Don't print anything."
        )

    def handle(self, *args, **options):
        if options["execute"]:
            print("This will permanently delete and/or anonymize user data.")
            print("Proceed? (Y/n)")
            confirm = input(": ")
            if confirm != "Y":
                return

        results = apply_data_retention(
            preview=not options["execute"],
            show_progress=not options["silent"]
        )

        print()
        if options["execute"]:
            print("SUMMARY")
            for model, summary in results.items():
                print(model)
                if deleted := summary.get("deleted"):
                    print(f"- Deleted: {deleted}")
                if anonymized := summary.get("anonymized"):
                    print(f"- Anonymized: {anonymized}")
        else:
            menu = ResultExplorer(results)
            menu.run()


class ResultExplorer:

    def __init__(self, result_data):
        self.data = result_data
        self.keymap = {}
        for i, key in enumerate(sorted(self.data.keys()), start=1):
            self.keymap[str(i)] = key

    def _prompt_from_choices(self, prompt_text, choices):
        while True:
            choice = input(prompt_text)
            if choice == "" or choice in choices:
                return choice

    def _get_model_attribute(self, model_inst, attribute):
        steps = attribute.split(".")
        value = model_inst
        while steps:
            step = steps.pop(0)
            value = getattr(value, step)

        return value

    def list_affected_models(self):
        for i, model in self.keymap.items():
            print(f"{i:2}: {model}")

    def explore_model(self, model):
        deletion = self.data[model].get("deleted", [])
        anonymization = self.data[model].get("anonymized", [])
        print("Model stats")
        print("1: Marked for deletion:", len(deletion))
        print("2: Marked for anonymization:", len(anonymization))
        print("R: Return")

        while True:
            print("Choose category to explore")
            category = input(": ")
            if category == "1":
                print("Exploring models marked for DELETION")
                self.explore_results(deletion)
            elif category == "2":
                print("Exploring models marked for ANONYMIZATON")
                self.explore_results(anonymization)
            elif category.lower() == "r":
                return

    def explore_results(self, result_list):
        print("Explore summaries of values")
        while True:
            attribute = input("Model attribute: ")
            if not attribute:
                return

            values = defaultdict(int)
            max_len = 0

            try:
                for result in result_list:
                    value = str(self._get_model_attribute(result, attribute))
                    values[value] += 1
                    max_len = max(len(value), max_len)
            except AttributeError:
                print("No matching attribute")
                continue

            keys = sorted(values.keys())

            for v in keys:
                print(f"{v:{max_len}} : {values[v]}")

    def run(self):
        print("DATA EXPLORER")

        while True:
            print("Main Menu")
            self.list_affected_models()
            key = self._prompt_from_choices("Choose model: ", list(self.keymap.keys()))
            if not key:
                confirm = input("Quit? (Y/n): ")
                if confirm == "Y":
                    break

            model = self.keymap[key]
            self.explore_model(model)
