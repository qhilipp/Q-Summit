import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI


def llm_init(deployment_name: str = "gpt-4o-mini", api_version: str = "2023-05-15") -> AzureChatOpenAI:
    # Load .env file (searches parent directories automatically)
    load_dotenv(override=True)
    # Validate critical environment variables
    required_vars = ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT"]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise ValueError(f"Missing environment variables: {', '.join(missing)}")
    
    return AzureChatOpenAI(  
        deployment_name=deployment_name,
        openai_api_key=os.environ["AZURE_OPENAI_API_KEY"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        openai_api_version=api_version,
    )

# LLM (Azure OpenAI) initialization
llm = llm_init()
# Test: 
#print(llm.invoke("Plan my next study abroad in 2025. Suprise me with an affordable destination at a Erasmus University.").content)
