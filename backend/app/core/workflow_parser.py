from typing import List, Dict, Any, Optional
from crewai import Agent, Task, Crew, Process
from langchain_community.tools import DuckDuckGoSearchRun
# Import other tools...

class WorkflowParser:
    """
    The Brain Trust Graph Engine.
    Translates visual React Flow JSON into executable CrewAI objects.
    """

    def __init__(self, workflow_json: Dict[str, Any]):
        self.nodes = {n['id']: n for n in workflow_json.get('nodes', [])}
        self.edges = workflow_json.get('edges', [])
        self.agents_map = {} # Map node_id -> Agent()
        self.tasks_map = {}  # Map node_id -> Task()

    def parse_graph(self) -> Crew:
        """
        Main entry point. 
        1. Creates Agents (with TELOS context from ~/.pai/)
        2. Creates Tasks (and links them)
        3. Returns a Crew object ready for kickoff()
        """
       
        # 1. Instantiate Agents from Nodes
        # We filter for nodes strictly of type 'agentNode'
        for node_id, node in self.nodes.items():
            if node.get('type') == 'agentNode':
                self.agents_map[node_id] = self._create_agent(node['data'])

        # 2. Instantiate Tasks & Link Dependencies
        # In a sequential flow, Edges define the Task sequence.
        # Node A -> Edge -> Node B means:
        # Task B depends on Task A (context from A is passed to B)
        
        # We need to sort tasks topologically or let CrewAI sequential process handle it.
        # For v1, let's assume a simple list based on the edge flow.
        
        tasks_list = []
        
        # Simple traversal for Sequential Process:
        # Find start node (no incoming edges)
        # Traverse down.
        # (This logic would be more complex for Process.hierarchical)
        sorted_node_ids = self._topological_sort()
        
        for node_id in sorted_node_ids:
            if node_id in self.agents_map:
                agent = self.agents_map[node_id]
                node_data = self.nodes[node_id]['data']
                
                # Create the task
                task = Task(
                    description=node_data.get('prompt', f"Execute role: {node_data.get('role', 'Agent')}"),
                    agent=agent,
                    expected_output="Detailed analysis and execution results."
                )
                tasks_list.append(task)
                self.tasks_map[node_id] = task

        # 3. Create Crew
        crew = Crew(
            agents=list(self.agents_map.values()),
            tasks=tasks_list,
            verbose=True, # Important for websocket streaming later
            process=Process.sequential 
        )
        return crew

    def _create_agent(self, data: Dict) -> Agent:
        """
        Hydrates a CrewAI Agent from Node Data with TELOS context and script tools.
        
        Loads personal context from ~/.pai/context/ and tools from ~/.pai/skills/
        
        Args:
            data: Node data from React Flow
        """
        import os
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_anthropic import ChatAnthropic
        from app.core.context_loader import ContextLoader
        from app.tools.script_execution_tool import ScriptRegistry

        # Load TELOS context
        loader = ContextLoader()
        try:
            context = loader.load_context()
        except FileNotFoundError as e:
            # Fallback: operate without TELOS (log warning)
            print(f"WARNING: {e}. Agent will operate without user context.")
            context = None
        
        # Build base backstory
        base_backstory = data.get('backstory', 'An AI assistant.')
        
        # Inject TELOS if available
        if context:
            enhanced_backstory = loader.inject_into_prompt(base_backstory, context)
        else:
            enhanced_backstory = base_backstory

        # Configure LLM
        model_name = data.get('model', 'gemini-2.0-flash')
        llm = None

        if 'gemini' in model_name:
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=os.getenv("GEMINI_API_KEY"),
                temperature=0.7
            )
        elif 'claude' in model_name:
            # Map friendly names to actual Anthropic Model IDs
            # Updated Jan 2025: Using current model IDs
            if "3-5" in model_name or "3.5" in model_name or "sonnet" in model_name.lower():
                ant_model = "claude-sonnet-4-20250514"
            elif "opus" in model_name:
                ant_model = "claude-opus-4-20250514"
            else:
                ant_model = "claude-sonnet-4-20250514"
            
            llm = ChatAnthropic(
                model_name=ant_model,
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                temperature=0.7
            )
        
        # Load script tools
        registry = ScriptRegistry()
        tools = registry.get_tools()
        
        # Add role-specific tools
        if 'librarian' in data.get('role', '').lower():
            from app.tools.drive_tool import DriveListTool, DriveReadTool, DriveWriteTool
            tools.extend([DriveListTool(), DriveReadTool(), DriveWriteTool()])

        return Agent(
            role=data.get('role', 'Assistant'),
            goal=data.get('goal', 'Help the user'),
            backstory=enhanced_backstory,  # Now includes TELOS context
            allow_delegation=False,
            tools=tools,  # Includes script tools + role-specific tools
            verbose=True,
            llm=llm
        )


    def _topological_sort(self) -> List[str]:
        """
        Determines execution order based on Edges using Kahn's Algorithm.
        """
        in_degree = {node_id: 0 for node_id in self.nodes}
        graph = {node_id: [] for node_id in self.nodes}

        for edge in self.edges:
            source = edge['source']
            target = edge['target']
            if source in graph and target in in_degree:
                graph[source].append(target)
                in_degree[target] += 1

        queue = [node_id for node_id in self.nodes if in_degree[node_id] == 0]
        sorted_order = []

        while queue:
            u = queue.pop(0)
            sorted_order.append(u)

            for v in graph[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)
        
        if len(sorted_order) != len(self.nodes):
            # Cycle detected or disconnected components handling
            # Fallback for now to just return what we have + remaining
            remaining = [n for n in self.nodes if n not in sorted_order]
            return sorted_order + remaining

        return sorted_order 
