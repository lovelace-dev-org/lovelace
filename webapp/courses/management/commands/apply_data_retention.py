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

    def _prompt_from_choices(self, prompt_text, choices):
        while True:
            choice = input(prompt_text)
            if choice is None or choice in choices:
                return choice

    def list_affected_models(self):
        for model in sorted(self.data.keys()):
            print(model)

    def explore_model(self):
        model = self._prompt_from_choices("Choose model: ". list(self.data.keys()))
        if not model:
            return

        print("Model stats")
        print("Marked for deletion:", len(self.data[model].get("deleted", []))
        print("Marked for anonymization:", len(self.data[model].get("anonymized", [])

    def run(self):
        print("DATA EXPLORER")
        print("1: List affected models")
        print("2: Explore by model")
        print("Q: Quit explorer")

        while True:
            action = input("")
            if action == "1":
                self.list_affected_models()
            elif action == "2":
                self.explore_model(self)

            elif action == "Q":
                return


















