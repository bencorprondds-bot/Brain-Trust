"""
Brain Trust CrewAI Integration
Multi-agent collaboration using CrewAI framework
"""

from typing import Optional, Any, List
from crewai import Agent, Crew, Task, Process, LLM
from crewai.project import CrewBase, agent, crew, task
import os
from dotenv import load_dotenv
import google.generativeai as genai
from anthropic import Anthropic
import yaml

# Load environment variables
load_dotenv()

# Configure API clients
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

if ANTHROPIC_API_KEY:
    anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)


class GeminiLLM(LLM):
    """Custom LLM wrapper for Google Gemini API"""
    
    def __init__(self, model: str = "gemini-2.5-pro", **kwargs):
        super().__init__(model=model)
        self.model_name = model
        self._configure()
    
    def _configure(self):
        """Configure the Gemini client"""
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        genai.configure(api_key=GEMINI_API_KEY)
    
    def call(self, messages: List[dict], **kwargs) -> str:
        """Make API call to Gemini"""
        try:
            # Extract system instruction from first message if present
            system_instruction = None
            user_messages = []
            
            for msg in messages:
                if msg.get('role') == 'system':
                    system_instruction = msg.get('content', '')
                elif msg.get('role') in ['user', 'assistant']:
                    user_messages.append(msg.get('content', ''))
            
            # Combine all user messages
            prompt = '\n'.join(user_messages)
            
            # Create model with system instruction
            model_config = {
                'model_name': self.model_name
            }
            if system_instruction:
                model_config['system_instruction'] = system_instruction
            
            model_instance = genai.GenerativeModel(**model_config)
            response = model_instance.generate_content(prompt)
            
            return response.text
        except Exception as e:
            return f"Gemini API Error: {str(e)}"


class ClaudeLLM(LLM):
    """Custom LLM wrapper for Anthropic Claude API"""
    
    def __init__(self, model: str = "claude-sonnet-4-20250514", **kwargs):
        super().__init__(model=model)
        self.model_name = model
        self.client = None
        self._configure()
    
    def _configure(self):
        """Configure the Claude client"""
        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
        self.client = Anthropic(api_key=ANTHROPIC_API_KEY)
    
    def call(self, messages: List[dict], **kwargs) -> str:
        """Make API call to Claude"""
        try:
            # Separate system message from conversation
            system_msg = ""
            conversation = []
            
            for msg in messages:
                if msg.get('role') == 'system':
                    system_msg = msg.get('content', '')
                elif msg.get('role') in ['user', 'assistant']:
                    conversation.append({
                        'role': msg['role'],
                        'content': msg.get('content', '')
                    })
            
            # If no conversation messages, create one from system message
            if not conversation:
                conversation = [{'role': 'user', 'content': 'Hello'}]
            
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=1024,
                system=system_msg,
                messages=conversation
            )
            
            return response.content[0].text
        except Exception as e:
            return f"Claude API Error: {str(e)}"


@CrewBase
class BrainTrustCrew:
    """Brain Trust multi-agent crew"""
    
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    
    def __init__(self):
        # Load agent configurations from JSON to get model info
        self.agent_models = self._load_agent_models()
    
    def _load_agent_models(self):
        """Load agent model configurations from agents.json"""
        import json
        try:
            with open('agents.json', 'r', encoding='utf-8-sig') as f:
                agents = json.load(f)
                return {agent['id']: agent for agent in agents}
        except FileNotFoundError:
            return {}
    
    @agent
    def aria_agent(self) -> Agent:
        """ARIA - Strategic CEO"""
        agent_config = self.agent_models.get('aria', {})
        model = agent_config.get('model', 'gemini-2.5-pro')
        
        return Agent(
            config=self.agents_config['aria'],
            llm=GeminiLLM(model=model),
            verbose=True
        )
    
    @agent
    def vector_agent(self) -> Agent:
        """VECTOR - Abrasive Engineer"""
        agent_config = self.agent_models.get('vector', {})
        model = agent_config.get('model', 'claude-sonnet-4-20250514')
        
        return Agent(
            config=self.agents_config['vector'],
            llm=ClaudeLLM(model=model),
            verbose=True
        )
    
    @agent
    def marcus_agent(self) -> Agent:
        """MARCUS - Sci-Fi Novelist"""
        agent_config = self.agent_models.get('marcus', {})
        model = agent_config.get('model', 'gemini-2.5-pro')
        
        return Agent(
            config=self.agents_config['marcus'],
            llm=GeminiLLM(model=model),
            verbose=True
        )
    
    @agent
    def echo_agent(self) -> Agent:
        """ECHO - Reflection Guide"""
        agent_config = self.agent_models.get('echo', {})
        model = agent_config.get('model', 'claude-sonnet-4-20250514')
        
        return Agent(
            config=self.agents_config['echo'],
            llm=ClaudeLLM(model=model),
            verbose=True
        )
    
    @task
    def strategic_analysis_task(self) -> Task:
        """Strategic business analysis task"""
        return Task(
            config=self.tasks_config['strategic_analysis'],
            agent=self.aria_agent()
        )
    
    @task
    def technical_critique_task(self) -> Task:
        """Technical engineering critique task"""
        return Task(
            config=self.tasks_config['technical_critique'],
            agent=self.vector_agent()
        )
    
    @task
    def creative_vision_task(self) -> Task:
        """Creative storytelling perspective task"""
        return Task(
            config=self.tasks_config['creative_vision'],
            agent=self.marcus_agent()
        )
    
    @task
    def reflective_synthesis_task(self) -> Task:
        """Reflective synthesis and questions task"""
        return Task(
            config=self.tasks_config['reflective_synthesis'],
            agent=self.echo_agent()
        )
    
    @crew
    def crew(self) -> Crew:
        """Creates the Brain Trust Crew"""
        return Crew(
            agents=self.agents,  # Automatically created by @agent decorator
            tasks=self.tasks,    # Automatically created by @task decorator
            process=Process.sequential,
            verbose=True,
        )
    
    def run_workflow(self, user_input: str, agent_sequence: Optional[List[str]] = None) -> str:
        """
        Run a multi-agent workflow
        
        Args:
            user_input: The user's question or task
            agent_sequence: Optional list of agent names to use (e.g., ['aria', 'vector'])
                          If None, uses all agents in default sequence
        
        Returns:
            The final output from the sequential workflow
        """
        # For now, run all tasks in sequence
        # Future enhancement: dynamically select tasks based on agent_sequence
        result = self.crew().kickoff(inputs={'user_request': user_input})
        return str(result)


if __name__ == '__main__':
    # Test the crew
    print("Initializing Brain Trust Crew...")
    brain_trust = BrainTrustCrew()
    print("Crew initialized successfully!")
    
    # Test workflow
    test_input = "What should our product development strategy be for Q1?"
    print(f"\nTesting workflow with input: {test_input}")
    result = brain_trust.run_workflow(test_input)
    print(f"\nWorkflow result:\n{result}")
