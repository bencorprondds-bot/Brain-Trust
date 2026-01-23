from flask import Flask, render_template, request, jsonify
import json
import os
import time
from dotenv import load_dotenv
import google.generativeai as genai
from anthropic import Anthropic
from job_manager import JobManager

# Load environment variables
load_dotenv()

app = Flask(__name__)
job_manager = JobManager()

# Configure API clients
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

if ANTHROPIC_API_KEY:
    anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)

# Path to agents configuration
AGENTS_FILE = 'agents.json'

def load_agents():
    """Load agents from JSON file"""
    try:
        with open(AGENTS_FILE, 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_agents(agents):
    """Save agents to JSON file"""
    with open(AGENTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(agents, f, indent=2, ensure_ascii=False)

def call_gemini_api(prompt, system_prompt, model="gemini-2.0-flash-exp"):
    """Call Gemini API"""
    try:
        if not GEMINI_API_KEY:
            return "Error: Gemini API key not configured. Please add GEMINI_API_KEY to your .env file."
        
        model_instance = genai.GenerativeModel(
            model_name=model,
            system_instruction=system_prompt
        )
        
        response = model_instance.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Gemini API Error: {str(e)}"

def call_claude_api(prompt, system_prompt, model="claude-3-5-sonnet-20241022"):
    """Call Claude API"""
    try:
        if not ANTHROPIC_API_KEY:
            return "Error: Claude API key not configured. Please add ANTHROPIC_API_KEY to your .env file."
        
        response = anthropic_client.messages.create(
            model=model,
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.content[0].text
    except Exception as e:
        return f"Claude API Error: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/agents', methods=['GET'])
def get_agents():
    """Get all agents"""
    agents = load_agents()
    return jsonify(agents)

@app.route('/agents', methods=['POST'])
def create_agent():
    """Create a new agent"""
    data = request.json
    agents = load_agents()
    
    # Generate ID from name
    agent_id = data['name'].lower().replace(' ', '_')
    
    new_agent = {
        'id': agent_id,
        'name': data['name'],
        'role': data['role'],
        'icon': data.get('icon', '●'),
        'color': data['color'],
        'api_provider': data['api_provider'],
        'model': data['model'],
        'system_prompt': data['system_prompt']
    }
    
    agents.append(new_agent)
    save_agents(agents)
    
    return jsonify(new_agent), 201

@app.route('/agents/<agent_id>', methods=['PUT'])
def update_agent(agent_id):
    """Update an existing agent"""
    data = request.json
    agents = load_agents()
    
    for i, agent in enumerate(agents):
        if agent['id'] == agent_id:
            agents[i] = {
                'id': agent_id,
                'name': data['name'],
                'role': data['role'],
                'icon': data.get('icon', agent['icon']),
                'color': data['color'],
                'api_provider': data['api_provider'],
                'model': data['model'],
                'system_prompt': data['system_prompt']
            }
            save_agents(agents)
            return jsonify(agents[i])
    
    return jsonify({'error': 'Agent not found'}), 404

@app.route('/agents/<agent_id>', methods=['DELETE'])
def delete_agent(agent_id):
    """Delete an agent"""
    agents = load_agents()
    agents = [a for a in agents if a['id'] != agent_id]
    save_agents(agents)
    return jsonify({'success': True})

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages and route to appropriate AI"""
    data = request.json
    message = data.get('message', '')
    agent_id = data.get('agent_id', '').lower()
    
    agents = load_agents()
    agent = next((a for a in agents if a['id'] == agent_id), None)
    
    if not agent:
        return jsonify({'error': 'Invalid agent'}), 400
    
    # Route to appropriate API
    if agent['api_provider'] == 'gemini':
        response_text = call_gemini_api(
            message, 
            agent['system_prompt'],
            agent.get('model', 'gemini-2.0-flash-exp')
        )
    elif agent['api_provider'] == 'claude':
        response_text = call_claude_api(
            message,
            agent['system_prompt'],
            agent.get('model', 'claude-3-5-sonnet-20241022')
        )
    else:
        response_text = f"Error: Unknown API provider '{agent['api_provider']}'"
    
    response = {
        'agent': agent['name'],
        'message': response_text,
        'color': agent['color'],
        'api_provider': agent['api_provider']
    }
    
    return jsonify(response)

@app.route('/workflow', methods=['POST'])
def run_workflow_sync():
    """Execute multi-agent collaborative workflow synchronously (Legacy)"""
    return run_workflow_logic(request.json)

def run_workflow_logic(data):
    """Shared logic for running workflow"""
    try:
        from brain_trust_crew import BrainTrustCrew
        
        user_input = data.get('task', '')
        agent_sequence = data.get('agents', None)
        
        if not user_input:
            return {'error': 'Task description required'}
        
        crew = BrainTrustCrew()
        result = crew.run_workflow(user_input, agent_sequence)
        
        return {
            'result': result,
            'agents_used': agent_sequence or ['aria', 'vector', 'marcus', 'echo'],
            'success': True
        }
    except Exception as e:
        return {'error': str(e)}

@app.route('/jobs/start', methods=['POST'])
def start_job():
    """Start a background agent job"""
    data = request.json
    
    def job_wrapper(job_data):
        result = run_workflow_logic(job_data)
        if 'error' in result:
            raise Exception(result['error'])
        return result

    job_id = job_manager.submit_job(job_wrapper, data)
    return jsonify({'job_id': job_id, 'status': 'queued'})

@app.route('/jobs/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get status of a specific job"""
    job = job_manager.get_job(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(job)

@app.route('/jobs', methods=['GET'])
def list_jobs():
    """List all jobs"""
    return jsonify(job_manager.list_jobs())


if __name__ == '__main__':
    app.run(debug=True, port=5000)
