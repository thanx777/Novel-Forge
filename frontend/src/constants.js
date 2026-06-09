export const NODE_TYPES = {
  manager: {
    label: 'Manager',
    category: 'Control',
    color: '#58a6ff',
    defaultPorts: {
      inputs: [{ id: 'inp_feedback', name: 'feedback' }, { id: 'inp_coordinate', name: 'coordinate' }],
      outputs: [{ id: 'out_dispatch', name: 'dispatch' }, { id: 'out_coordinate', name: 'coordinate' }, { id: 'out_broadcast', name: 'broadcast' }]
    }
  },
  worker: {
    label: 'Worker',
    category: 'Execution',
    color: '#3fb950',
    defaultPorts: {
      inputs: [{ id: 'inp_task', name: 'task' }],
      outputs: [{ id: 'out_result', name: 'result' }]
    }
  },
  reviewer: {
    label: 'Reviewer',
    category: 'Quality',
    color: '#d29922',
    defaultPorts: {
      inputs: [{ id: 'inp_code', name: 'code' }, { id: 'inp_result', name: 'result' }],
      outputs: [{ id: 'out_review', name: 'review' }, { id: 'out_feedback', name: 'feedback' }]
    }
  },
}

export const API_FORMATS = {
  openai: {
    label: 'OpenAI Compatible',
    baseUrlExample: 'https://api.openai.com/v1',
    modelExamples: ['gpt-4', 'gpt-3.5-turbo', 'glm-4-flash', 'claude-3-haiku']
  },
  claude: {
    label: 'Anthropic Claude',
    baseUrlExample: 'https://api.anthropic.com',
    modelExamples: ['claude-3-5-sonnet-20241022', 'claude-3-opus-20240229']
  }
}

export const NODE_W = 220
export const HEADER_H = 36
export const API_BASE = 'http://127.0.0.1:8000/api'
