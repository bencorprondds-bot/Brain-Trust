from typing import List, Dict, Any
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
        1. Creates Agents
        2. Creates Tasks (and links them)
        3. Returns a Crew object ready for kickoff()
        """
       
        # 1. Instantiate Agents from Nodes
        # We filter for nodes strictly of type 'agentNode'
        for node_id, node in self.nodes.items():
            if node['type'] == 'agentNode':
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
                    description=node_data.get('prompt', f"Execute role: {node_data['role']}"),
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
        """Hydrates a CrewAI Agent from Node Data"""
        return Agent(
            role=data.get('role', 'Assistant'),
            goal=data.get('goal', 'Help the user'),
            backstory=data.get('backstory', 'An AI assistant.'),
            allow_delegation=False,
            # Tools would be dynamically rejected/selected here based on your "Router" logic
            # tools=[DuckDuckGoSearchRun()] if 'research' in data['tags'] else [],
            verbose=True
        )

    def _topological_sort(self) -> List[str]:
        """
        Determines execution order based on Edges.
        Standard Kahn's algorithm or DFS.
        """
        # Placeholder for simple sort implementation
        # For now, just returning keys to illustrate
        return list(self.nodes.keys()) 
