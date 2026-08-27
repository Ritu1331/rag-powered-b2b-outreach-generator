import streamlit as st

from langchain_community.document_loaders import WebBaseLoader

from chains import Chain
from portfolio import Portfolio


# ================================================================
# PAGE CONFIG
# ================================================================

st.set_page_config(
    page_title="RAG-Powered B2B Outreach Generator",
    page_icon="📧",
    layout="wide"
)


# ================================================================
# MAIN APPLICATION
# ================================================================

def create_streamlit_app():

    st.title("📧 RAG-Powered B2B Outreach Generator")

    st.write(
        "Enter a job listing page or a single job posting URL."
    )

    # ------------------------------------------------------------
    # URL INPUT
    # ------------------------------------------------------------

    url = st.text_input(
        "Enter a URL:",
        placeholder="https://example.com/careers"
    )

    # ------------------------------------------------------------
    # GENERATE BUTTON
    # ------------------------------------------------------------

    if st.button(
        "Generate Emails",
        type="primary"
    ):

        if not url.strip():

            st.error(
                "Please enter a job URL."
            )

            return

        try:

            # ====================================================
            # INITIALIZE
            # ====================================================

            llm = Chain()

            portfolio = Portfolio()

            # ====================================================
            # LOAD WEBPAGE
            # ====================================================

            with st.spinner(
                "Loading webpage..."
            ):

                loader = WebBaseLoader(
                    url
                )

                documents = loader.load()

            # ====================================================
            # CHECK DOCUMENT
            # ====================================================

            if not documents:

                st.error(
                    "Could not extract content from this webpage."
                )

                return

            # ====================================================
            # COMBINE PAGE TEXT
            # ====================================================

            page_text = "\n\n".join(
                document.page_content
                for document in documents
                if document.page_content
            )

            if not page_text.strip():

                st.error(
                    "The webpage contains no readable text."
                )

                return

            # ====================================================
            # EXTRACT JOBS
            # ====================================================

            with st.spinner(
                "Extracting job information..."
            ):

                jobs = llm.extract_jobs(
                    page_text,
                    source_url=url
                )

            # ====================================================
            # SAFETY
            #
            # NEVER allow more than 3 jobs for testing.
            # ====================================================

            jobs = jobs[:3]

            if not jobs:

                st.error(
                    "No jobs could be extracted."
                )

                return

            # ====================================================
            # SUCCESS MESSAGE
            # ====================================================

            st.success(
                f"Found {len(jobs)} job posting(s)."
            )

            # ====================================================
            # GENERATE ONE EMAIL PER JOB
            # ====================================================

            for index, job in enumerate(
                jobs,
                start=1
            ):

                role = job.get(
                    "role",
                    "Unknown Role"
                )

                # ------------------------------------------------
                # JOB HEADER
                # ------------------------------------------------

                st.header(
                    f"📌 Job {index}: {role}"
                )

                # ------------------------------------------------
                # EXTRACTED JOB DATA
                # ------------------------------------------------

                with st.expander(
                    "View extracted job information"
                ):

                    st.write(
                        "**Role:**",
                        job.get(
                            "role",
                            ""
                        )
                    )

                    st.write(
                        "**Experience:**",
                        job.get(
                            "experience",
                            ""
                        )
                    )

                    st.write(
                        "**Skills:**",
                        ", ".join(
                            job.get(
                                "skills",
                                []
                            )
                        )
                    )

                    st.write(
                        "**Description:**",
                        job.get(
                            "description",
                            ""
                        )
                    )

                # ------------------------------------------------
                # PORTFOLIO SEARCH
                # ------------------------------------------------

                try:

                    links = portfolio.query_links(
                        job.get(
                            "skills",
                            []
                        )
                    )

                except Exception as portfolio_error:

                    print(
                        "Portfolio error:",
                        portfolio_error
                    )

                    links = []

                # ------------------------------------------------
                # EMAIL
                # ------------------------------------------------

                with st.spinner(
                    f"Generating email for {role}..."
                ):

                    email = llm.write_mail(
                        job,
                        links
                    )

                # ------------------------------------------------
                # DISPLAY EMAIL
                # ------------------------------------------------

                st.subheader(
                    "✉️ Generated Cold Email"
                )

                st.caption(
                    "Copy your email from the box below:"
                )

                st.text_area(
                    f"Email {index}",
                    email,
                    height=350,
                    key=f"email_{index}"
                )

                # ------------------------------------------------
                # SEPARATOR
                # ------------------------------------------------

                if index < len(jobs):

                    st.divider()

        # ========================================================
        # ERROR HANDLING
        # ========================================================

        except Exception as e:

            st.error(
                f"An Error Occurred: {str(e)}"
            )

            with st.expander(
                "Show error details"
            ):

                st.exception(e)


# ================================================================
# RUN
# ================================================================

if __name__ == "__main__":

    create_streamlit_app()