from dotenv import load_dotenv

from employer_dd_agent.api import create_app
from employer_dd_agent.observability import initialize_observability

load_dotenv()
initialize_observability()

app = create_app()
