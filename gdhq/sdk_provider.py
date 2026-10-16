"""OPTIONAL OpenAI Agents SDK agent runner backed exclusively by LM Studio loopback.

Not required for the standalone distribution. No cloud endpoint, no tracing, no tools.
"""
from .providers import LMStudio, ModelUnavailable
from .settings import local_endpoint

class AgentsSDKLocal(LMStudio):
    def __init__(self,url='http://127.0.0.1:1234/v1',timeout=90):
        super().__init__(local_endpoint(url),timeout)
    def chat(self,system,user,model,max_tokens=1100):
        if not model:raise ModelUnavailable('Choisis un modèle local dans LM Studio.')
        try:
            from agents import Agent, Runner, RunConfig, ModelSettings, OpenAIChatCompletionsModel
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise ModelUnavailable('OpenAI Agents SDK n’est pas installé. Reviens au moteur natif ou installe le SDK optionnel.') from exc
        import asyncio
        async def execute():
            client=AsyncOpenAI(base_url=self.url,api_key='lm-studio-local',timeout=self.timeout,max_retries=0)
            try:
                llm=OpenAIChatCompletionsModel(model=model,openai_client=client)
                agent=Agent(name='Global métier local',instructions=system,model=llm,model_settings=ModelSettings(max_tokens=max_tokens),tools=[])
                result=await Runner.run(agent,user,max_turns=1,run_config=RunConfig(tracing_disabled=True))
                output=result.final_output
                if not isinstance(output,str) or not output.strip():raise ModelUnavailable('Aucune réponse textuelle du modèle SDK local.')
                return output.strip()
            finally:
                await client.close()
        try:return asyncio.run(execute())
        except ModelUnavailable:raise
        except Exception as exc:raise ModelUnavailable('Erreur OpenAI Agents SDK local : '+type(exc).__name__) from exc
