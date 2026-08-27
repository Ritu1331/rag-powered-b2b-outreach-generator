import os
import pandas as pd


class Portfolio:

    def __init__(
        self,
        file_path="resource/my_portfolio.csv"
    ):

        self.file_path = file_path
        self.data = None

    # =========================================================
    # LOAD PORTFOLIO
    # =========================================================

    def load_portfolio(self):

        if not os.path.exists(self.file_path):

            print(
                f"Portfolio file not found: "
                f"{self.file_path}"
            )

            self.data = pd.DataFrame(
                columns=[
                    "techstack",
                    "links"
                ]
            )

            return

        self.data = pd.read_csv(
            self.file_path
        )

        # Make sure expected columns exist
        if "techstack" not in self.data.columns:

            raise ValueError(
                "portfolio.csv must contain "
                "'techstack' column."
            )

        if "links" not in self.data.columns:

            raise ValueError(
                "portfolio.csv must contain "
                "'links' column."
            )

    # =========================================================
    # QUERY RELEVANT LINKS
    # =========================================================

    def query_links(self, skills):

        if self.data is None:

            self.load_portfolio()

        if self.data.empty:

            return []

        if not skills:

            return []

        skill_words = {
            str(skill).lower().strip()
            for skill in skills
            if str(skill).strip()
        }

        results = []

        for _, row in self.data.iterrows():

            techstack = str(
                row["techstack"]
            ).lower()

            link = str(
                row["links"]
            ).strip()

            score = 0

            for skill in skill_words:

                if skill in techstack:

                    score += 1

            if score > 0 and link:

                results.append(
                    (
                        score,
                        link
                    )
                )

        # Highest matching score first
        results.sort(
            key=lambda x: x[0],
            reverse=True
        )

        # Only top 3
        return [
            link
            for _, link in results[:3]
        ]