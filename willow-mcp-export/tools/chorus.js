/**
 * Chorus Tools
 *
 * Multi-perspective feedback using different personas and models
 */

import Anthropic from '@anthropic-ai/sdk';

let anthropicClient = null;

function getAnthropic() {
  if (anthropicClient) return anthropicClient;

  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    throw new Error('ANTHROPIC_API_KEY must be set for chorus features');
  }

  anthropicClient = new Anthropic({ apiKey });
  return anthropicClient;
}

// Editorial personas for varied feedback
const PERSONAS = {
  harsh_critic: {
    name: 'The Harsh Critic',
    prompt: `You are a demanding literary critic who has seen it all. You don't give empty praise - you identify weaknesses, plot holes, pacing issues, and areas that need work. Be specific and constructive, but don't sugarcoat. Focus on:
- Structural problems
- Pacing issues
- Character inconsistencies
- Weak prose or clichés
- Logic gaps`,
  },
  supportive_reader: {
    name: 'The Supportive Reader',
    prompt: `You are an enthusiastic reader who loves discovering new stories. You focus on what's working well and what resonates emotionally. Identify:
- Moments that land emotionally
- Characters you connect with
- Scenes that pull you in
- Lines or passages that shine
- What makes you want to keep reading`,
  },
  copy_editor: {
    name: 'The Copy Editor',
    prompt: `You are a meticulous copy editor focused on clarity and polish. You catch:
- Unclear sentences or awkward phrasing
- Redundancy and wordiness
- Inconsistent style or tone
- Grammar and punctuation issues
- Opportunities to tighten prose`,
  },
  genre_expert: {
    name: 'The Genre Expert',
    prompt: `You are an expert in genre conventions and reader expectations. You evaluate:
- How well the piece fits its genre
- Tropes used effectively vs. feeling stale
- Pacing appropriate for the genre
- Reader expectations being met or subverted intentionally
- Market positioning`,
  },
  character_analyst: {
    name: 'The Character Analyst',
    prompt: `You focus exclusively on character development and authenticity. You examine:
- Character voice consistency
- Motivation clarity
- Emotional authenticity
- Character arc progression
- Dialogue that sounds natural for each character`,
  },
  devil_advocate: {
    name: "The Devil's Advocate",
    prompt: `You challenge assumptions and look for alternative interpretations. You ask:
- What if this choice is wrong?
- How might readers misinterpret this?
- What's the strongest argument against this approach?
- What are we not seeing?
- What would make this fail?`,
  },
};

// Tool definitions
export const chorusTools = [
  {
    name: 'chorus_get_feedback',
    description:
      'Get feedback from a specific editorial persona. Use this for targeted critique from a particular perspective.',
    inputSchema: {
      type: 'object',
      properties: {
        content: {
          type: 'string',
          description: 'The writing to get feedback on',
        },
        persona: {
          type: 'string',
          enum: Object.keys(PERSONAS),
          description: 'Which persona to get feedback from',
        },
        focus: {
          type: 'string',
          description: 'Optional: specific aspect to focus feedback on',
        },
      },
      required: ['content', 'persona'],
    },
  },
  {
    name: 'chorus_full_review',
    description:
      'Get feedback from multiple personas at once. Returns a comprehensive multi-perspective review. Uses Haiku for cost efficiency.',
    inputSchema: {
      type: 'object',
      properties: {
        content: {
          type: 'string',
          description: 'The writing to review',
        },
        personas: {
          type: 'array',
          items: {
            type: 'string',
            enum: Object.keys(PERSONAS),
          },
          description:
            'Which personas to include (default: harsh_critic, supportive_reader, copy_editor)',
        },
      },
      required: ['content'],
    },
  },
  {
    name: 'chorus_quick_takes',
    description:
      'Get multiple quick reactions using varied temperature settings. Useful for exploring different directions.',
    inputSchema: {
      type: 'object',
      properties: {
        content: {
          type: 'string',
          description: 'The writing or idea to react to',
        },
        question: {
          type: 'string',
          description: 'Specific question to answer about the content',
        },
        num_takes: {
          type: 'number',
          description: 'Number of different takes to generate (default 3, max 5)',
          default: 3,
        },
      },
      required: ['content', 'question'],
    },
  },
  {
    name: 'chorus_consensus',
    description:
      'After getting multiple pieces of feedback, synthesize them into actionable recommendations.',
    inputSchema: {
      type: 'object',
      properties: {
        feedback_items: {
          type: 'array',
          items: { type: 'string' },
          description: 'Array of feedback strings to synthesize',
        },
        original_content: {
          type: 'string',
          description: 'The original content that was reviewed',
        },
      },
      required: ['feedback_items'],
    },
  },
  {
    name: 'chorus_list_personas',
    description: 'List all available editorial personas and their focus areas.',
    inputSchema: {
      type: 'object',
      properties: {},
    },
  },
];

// Tool handlers
export async function handleChorusTool(name, args) {
  switch (name) {
    case 'chorus_get_feedback': {
      const anthropic = getAnthropic();
      const persona = PERSONAS[args.persona];

      if (!persona) {
        throw new Error(`Unknown persona: ${args.persona}`);
      }

      let systemPrompt = persona.prompt;
      if (args.focus) {
        systemPrompt += `\n\nFocus especially on: ${args.focus}`;
      }

      const response = await anthropic.messages.create({
        model: 'claude-3-5-haiku-20241022',
        max_tokens: 1024,
        system: systemPrompt,
        messages: [
          {
            role: 'user',
            content: `Please review this writing:\n\n${args.content}`,
          },
        ],
      });

      const feedback = response.content[0].text;

      return {
        content: [
          {
            type: 'text',
            text: `## ${persona.name}\n\n${feedback}`,
          },
        ],
      };
    }

    case 'chorus_full_review': {
      const anthropic = getAnthropic();
      const selectedPersonas = args.personas || [
        'harsh_critic',
        'supportive_reader',
        'copy_editor',
      ];

      // Run all personas in parallel
      const feedbackPromises = selectedPersonas.map(async (personaKey) => {
        const persona = PERSONAS[personaKey];
        if (!persona) return null;

        const response = await anthropic.messages.create({
          model: 'claude-3-5-haiku-20241022',
          max_tokens: 800,
          system: persona.prompt,
          messages: [
            {
              role: 'user',
              content: `Please review this writing (be concise but specific):\n\n${args.content}`,
            },
          ],
        });

        return {
          persona: persona.name,
          feedback: response.content[0].text,
        };
      });

      const results = await Promise.all(feedbackPromises);
      const validResults = results.filter((r) => r !== null);

      let response = '# Multi-Perspective Review\n\n';
      for (const r of validResults) {
        response += `## ${r.persona}\n\n${r.feedback}\n\n---\n\n`;
      }

      return { content: [{ type: 'text', text: response }] };
    }

    case 'chorus_quick_takes': {
      const anthropic = getAnthropic();
      const numTakes = Math.min(args.num_takes || 3, 5);

      // Different temperatures for variety
      const temperatures = [0.3, 0.6, 0.9, 1.0, 0.5].slice(0, numTakes);

      const takePromises = temperatures.map(async (temp, i) => {
        const response = await anthropic.messages.create({
          model: 'claude-3-5-haiku-20241022',
          max_tokens: 300,
          temperature: temp,
          messages: [
            {
              role: 'user',
              content: `Given this content:\n\n${args.content}\n\nAnswer this question in 2-3 sentences: ${args.question}`,
            },
          ],
        });

        return {
          take: i + 1,
          temperature: temp,
          response: response.content[0].text,
        };
      });

      const takes = await Promise.all(takePromises);

      let response = `# Quick Takes: "${args.question}"\n\n`;
      for (const t of takes) {
        response += `**Take ${t.take}** (temp ${t.temperature}):\n${t.response}\n\n`;
      }

      return { content: [{ type: 'text', text: response }] };
    }

    case 'chorus_consensus': {
      const anthropic = getAnthropic();

      const feedbackList = args.feedback_items
        .map((f, i) => `Feedback ${i + 1}:\n${f}`)
        .join('\n\n---\n\n');

      const response = await anthropic.messages.create({
        model: 'claude-3-5-haiku-20241022',
        max_tokens: 1024,
        system:
          'You synthesize multiple pieces of feedback into clear, actionable recommendations. Identify areas of agreement, note significant disagreements, and prioritize what to address first.',
        messages: [
          {
            role: 'user',
            content: `Synthesize this feedback into actionable recommendations:\n\n${feedbackList}${args.original_content ? `\n\nOriginal content being reviewed:\n${args.original_content.slice(0, 500)}...` : ''}`,
          },
        ],
      });

      return {
        content: [
          {
            type: 'text',
            text: `## Consensus Synthesis\n\n${response.content[0].text}`,
          },
        ],
      };
    }

    case 'chorus_list_personas': {
      let response = '# Available Editorial Personas\n\n';

      for (const [key, persona] of Object.entries(PERSONAS)) {
        response += `## ${persona.name}\n`;
        response += `Key: \`${key}\`\n\n`;
        response += `${persona.prompt.split('\n')[0]}\n\n`;
      }

      return { content: [{ type: 'text', text: response }] };
    }

    default:
      throw new Error(`Unknown chorus tool: ${name}`);
  }
}
