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
        2. Creates Tasks (and links them via context parameter)
        3. Returns a Crew object ready for kickoff()

        CRITICAL: Uses edge relationships to pass context between tasks.
        If Librarian (Task A) -> Writer (Task B), then Task B receives
        Task A's output via CrewAI's context parameter.
        """

        # 1. Instantiate Agents from Nodes
        # We filter for nodes strictly of type 'agentNode'
        for node_id, node in self.nodes.items():
            if node.get('type') == 'agentNode':
                self.agents_map[node_id] = self._create_agent(node['data'])

        # 2. Build dependency map from edges
        # upstream_tasks[node_id] = list of node_ids that feed INTO this node
        upstream_map: Dict[str, List[str]] = {node_id: [] for node_id in self.nodes}
        for edge in self.edges:
            source = edge.get('source')
            target = edge.get('target')
            if source and target and target in upstream_map:
                upstream_map[target].append(source)

        # 3. Instantiate Tasks & Link Dependencies via context
        # Node A -> Edge -> Node B means:
        # Task B depends on Task A (context from A is passed to B)

        tasks_list = []

        # Sort topologically to ensure upstream tasks are created first
        sorted_node_ids = self._topological_sort()

        for node_id in sorted_node_ids:
            if node_id in self.agents_map:
                agent = self.agents_map[node_id]
                node_data = self.nodes[node_id]['data']

                # Create the task description
                task_description = (
                    node_data.get('prompt')
                    or node_data.get('goal')
                    or f"Execute role: {node_data.get('role', 'Agent')}"
                )

                role_name = node_data.get('role', '')
                if 'librarian' in role_name.lower():
                    task_description += (
                        "\n\nIMPORTANT: Use the available Google Drive tools to "
                        "perform the task. Return the tool output verbatim without "
                        "paraphrasing. If a tool returns IDs, include them in your "
                        "final answer exactly as provided. Wrap file IDs in "
                        "<FETCHED_FILES>['id1', 'id2']</FETCHED_FILES> tags."
                    )

                # Get upstream tasks whose output should be passed as context
                upstream_node_ids = upstream_map.get(node_id, [])
                context_tasks = [
                    self.tasks_map[uid]
                    for uid in upstream_node_ids
                    if uid in self.tasks_map
                ]

                # Add context instruction to non-librarian agents that have upstream context
                if context_tasks and 'librarian' not in role_name.lower():
                    upstream_names = [
                        self.nodes[uid]['data'].get('name', uid)
                        for uid in upstream_node_ids
                        if uid in self.nodes
                    ]
                    task_description += (
                        f"\n\nCRITICAL: You MUST use the context provided by the "
                        f"previous agent(s): {', '.join(upstream_names)}. "
                        f"Their output contains the specific information you need. "
                        f"Do NOT invent or hallucinate information that wasn't provided. "
                        f"If the context mentions specific characters, files, or data, "
                        f"use ONLY that information."
                    )

                task = Task(
                    description=task_description,
                    agent=agent,
                    expected_output="Detailed analysis and execution results.",
                    context=context_tasks if context_tasks else None
                )
                tasks_list.append(task)
                self.tasks_map[node_id] = task

        # 3. Create Crew
        crew = Crew(
            agents=list(self.agents_map.values()),
            tasks=tasks_list,
            verbose=True, # Important for websocket streaming later
            process=Process.sequential,
            memory=False, # Disable ChromaDB/Embedding overhead to prevent crashes
            embedder=None 
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
        
        # Initialize tools list - prioritize CrewAI tools over scripts
        tools = []
        
        # Add role-specific CrewAI tools FIRST (agents try tools in order)
        if 'librarian' in data.get('role', '').lower():
            from app.tools.drive_tool import (
                DriveListTool, DriveReadTool, DriveWriteTool, 
                FindFolderTool, DocsEditTool, WordDocExportTool
            )
            tools.extend([
                DriveListTool(), 
                DriveReadTool(), 
                DriveWriteTool(), 
                FindFolderTool(),
                DocsEditTool(),
                WordDocExportTool()
            ])
        
        # Add writer/editor tools
        if any(keyword in data.get('role', '').lower() for keyword in ['writer', 'editor', 'creative']):
            from app.tools.drive_tool import DocsEditTool, DriveReadTool, WordDocExportTool
            tools.extend([DocsEditTool(), DriveReadTool(), WordDocExportTool()])
        
        # Load script tools LAST (fallback only)
        registry = ScriptRegistry()
        script_tools = registry.get_tools()
        tools.extend(script_tools)

        agent_kwargs = {
            "role": data.get('role', 'Assistant'),
            "goal": data.get('goal', 'Help the user'),
            "backstory": enhanced_backstory,  # Now includes TELOS context
            "allow_delegation": False,
            "tools": tools,  # Includes script tools + role-specific tools
            "verbose": True,
            "llm": llm,
        }

        # Reduce retries/iterations for Librarian during tests to avoid tool spam
        if 'librarian' in data.get('role', '').lower():
            import os
            max_iter_env = os.getenv("BRAIN_TRUST_MAX_ITER")
            try:
                max_iter_value = int(max_iter_env) if max_iter_env else 2
            except ValueError:
                max_iter_value = 2
            agent_kwargs["max_iter"] = max_iter_value

        return Agent(**agent_kwargs)


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
