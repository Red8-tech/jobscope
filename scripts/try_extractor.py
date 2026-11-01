import sys

from dotenv import load_dotenv

from jobscope.ai.extractor import SkillExtractor
from jobscope.ai.llm import GroqClient

DEFAULT_TEXT = "Senior backend engineer: Python, FastAPI, PostgreSQL, Docker on AWS."


def main() -> None:
    load_dotenv()
    text = " ".join(sys.argv[1:]) or DEFAULT_TEXT
    result = SkillExtractor(GroqClient()).extract(text)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()