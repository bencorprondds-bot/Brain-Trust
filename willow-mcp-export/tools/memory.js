/**
 * Memory Tools
 *
 * Persistent memory backed by Supabase for cross-session continuity
 */

import { createClient } from '@supabase/supabase-js';

// Initialize Supabase client
let supabase = null;

function getSupabase() {
  if (supabase) return supabase;

  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_KEY;

  if (!url || !key) {
    throw new Error('SUPABASE_URL and SUPABASE_KEY must be set');
  }

  supabase = createClient(url, key);
  return supabase;
}

// Tool definitions
export const memoryTools = [
  {
    name: 'memory_start_session',
    description:
      'Start a new creative session. Returns context from previous sessions, active projects, and your creative preferences. Call this at the beginning of each conversation.',
    inputSchema: {
      type: 'object',
      properties: {
        project_name: {
          type: 'string',
          description: 'Optional: specific project to focus on',
        },
      },
    },
  },
  {
    name: 'memory_end_session',
    description:
      'End the current session and save a summary. Call this before ending the conversation to preserve context for next time.',
    inputSchema: {
      type: 'object',
      properties: {
        summary: {
          type: 'string',
          description: 'Brief summary of what was accomplished this session',
        },
        decisions_made: {
          type: 'array',
          items: { type: 'string' },
          description: 'Key creative decisions made during this session',
        },
        open_questions: {
          type: 'array',
          items: { type: 'string' },
          description: 'Unresolved questions to address next time',
        },
      },
      required: ['summary'],
    },
  },
  {
    name: 'memory_get_project',
    description: 'Get details about a specific creative project.',
    inputSchema: {
      type: 'object',
      properties: {
        project_name: {
          type: 'string',
          description: 'Name of the project',
        },
      },
      required: ['project_name'],
    },
  },
  {
    name: 'memory_update_project',
    description: 'Update project status, word count, or other metadata.',
    inputSchema: {
      type: 'object',
      properties: {
        project_name: {
          type: 'string',
          description: 'Name of the project',
        },
        status: {
          type: 'string',
          enum: ['idea', 'outline', 'draft', 'revision', 'review', 'published'],
          description: 'Current project status',
        },
        word_count: {
          type: 'number',
          description: 'Current word count',
        },
        current_draft_id: {
          type: 'string',
          description: 'Google Drive file ID of current draft',
        },
        notes: {
          type: 'string',
          description: 'Additional notes about current state',
        },
      },
      required: ['project_name'],
    },
  },
  {
    name: 'memory_create_project',
    description: 'Create a new creative project to track.',
    inputSchema: {
      type: 'object',
      properties: {
        name: {
          type: 'string',
          description: 'Project name',
        },
        description: {
          type: 'string',
          description: 'Brief project description',
        },
        type: {
          type: 'string',
          enum: ['short_story', 'novel', 'article', 'script', 'other'],
          description: 'Type of creative work',
        },
      },
      required: ['name'],
    },
  },
  {
    name: 'memory_list_projects',
    description: 'List all creative projects.',
    inputSchema: {
      type: 'object',
      properties: {
        status: {
          type: 'string',
          enum: ['idea', 'outline', 'draft', 'revision', 'review', 'published', 'all'],
          description: 'Filter by status (default: all active)',
        },
      },
    },
  },
  {
    name: 'memory_record_lesson',
    description:
      'Record a creative lesson learned - what worked or did not work.',
    inputSchema: {
      type: 'object',
      properties: {
        lesson: {
          type: 'string',
          description: 'The insight or lesson learned',
        },
        category: {
          type: 'string',
          enum: ['voice', 'structure', 'pacing', 'character', 'dialogue', 'technique', 'process'],
          description: 'Category of the lesson',
        },
        worked: {
          type: 'boolean',
          description: 'Did this approach work well?',
        },
        project_name: {
          type: 'string',
          description: 'Optional: associated project',
        },
      },
      required: ['lesson', 'category', 'worked'],
    },
  },
  {
    name: 'memory_get_lessons',
    description: 'Retrieve creative lessons and preferences.',
    inputSchema: {
      type: 'object',
      properties: {
        category: {
          type: 'string',
          enum: ['voice', 'structure', 'pacing', 'character', 'dialogue', 'technique', 'process', 'all'],
          description: 'Filter by category (default: all)',
        },
        worked_only: {
          type: 'boolean',
          description: 'Only return things that worked',
        },
      },
    },
  },
  {
    name: 'memory_record_feedback',
    description: 'Record feedback received on a piece of writing.',
    inputSchema: {
      type: 'object',
      properties: {
        project_name: {
          type: 'string',
          description: 'Project the feedback is for',
        },
        source: {
          type: 'string',
          description: 'Source of feedback (e.g., "critic_persona", "haiku_chorus", "self")',
        },
        feedback: {
          type: 'string',
          description: 'The feedback content',
        },
        acted_on: {
          type: 'boolean',
          description: 'Was this feedback incorporated?',
        },
      },
      required: ['project_name', 'source', 'feedback'],
    },
  },
  {
    name: 'memory_search',
    description:
      'Search across all memory (projects, lessons, feedback, sessions) for relevant context.',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'What to search for',
        },
      },
      required: ['query'],
    },
  },
];

// Tool handlers
export async function handleMemoryTool(name, args) {
  const db = getSupabase();

  switch (name) {
    case 'memory_start_session': {
      // Get recent sessions
      const { data: sessions } = await db
        .from('sessions')
        .select('*')
        .order('ended_at', { ascending: false })
        .limit(3);

      // Get active projects
      const { data: projects } = await db
        .from('projects')
        .select('*')
        .neq('status', 'published')
        .order('updated_at', { ascending: false });

      // Get creative preferences (lessons that worked)
      const { data: lessons } = await db
        .from('creative_memory')
        .select('*')
        .eq('worked', true)
        .order('created_at', { ascending: false })
        .limit(10);

      // If specific project requested, get it
      let focusProject = null;
      if (args.project_name) {
        const { data } = await db
          .from('projects')
          .select('*')
          .ilike('name', `%${args.project_name}%`)
          .single();
        focusProject = data;
      }

      // Create new session
      const { data: session } = await db
        .from('sessions')
        .insert({
          started_at: new Date().toISOString(),
          project_id: focusProject?.id,
        })
        .select()
        .single();

      // Format response
      let response = '# Session Started\n\n';

      if (sessions?.length > 0) {
        response += '## Recent Sessions\n';
        for (const s of sessions) {
          response += `- ${s.ended_at?.slice(0, 10) || 'In progress'}: ${s.summary || 'No summary'}\n`;
          if (s.open_questions?.length > 0) {
            response += `  Open questions: ${s.open_questions.join(', ')}\n`;
          }
        }
        response += '\n';
      }

      if (focusProject) {
        response += `## Current Project: ${focusProject.name}\n`;
        response += `- Status: ${focusProject.status}\n`;
        response += `- Word count: ${focusProject.word_count || 'N/A'}\n`;
        if (focusProject.notes) {
          response += `- Notes: ${focusProject.notes}\n`;
        }
        response += '\n';
      } else if (projects?.length > 0) {
        response += '## Active Projects\n';
        for (const p of projects) {
          response += `- ${p.name} (${p.status}) - ${p.word_count || 0} words\n`;
        }
        response += '\n';
      }

      if (lessons?.length > 0) {
        response += '## Creative Preferences\n';
        for (const l of lessons) {
          response += `- [${l.category}] ${l.content}\n`;
        }
      }

      return {
        content: [{ type: 'text', text: response }],
        _meta: { session_id: session.id },
      };
    }

    case 'memory_end_session': {
      // Find current session (most recent without end time)
      const { data: currentSession } = await db
        .from('sessions')
        .select('*')
        .is('ended_at', null)
        .order('started_at', { ascending: false })
        .limit(1)
        .single();

      if (currentSession) {
        await db
          .from('sessions')
          .update({
            ended_at: new Date().toISOString(),
            summary: args.summary,
            decisions_made: args.decisions_made || [],
            open_questions: args.open_questions || [],
          })
          .eq('id', currentSession.id);
      }

      return {
        content: [
          {
            type: 'text',
            text: `Session ended. Summary saved:\n"${args.summary}"\n\nSee you next time!`,
          },
        ],
      };
    }

    case 'memory_get_project': {
      const { data: project } = await db
        .from('projects')
        .select('*')
        .ilike('name', `%${args.project_name}%`)
        .single();

      if (!project) {
        return {
          content: [
            { type: 'text', text: `Project "${args.project_name}" not found.` },
          ],
        };
      }

      // Get recent feedback for this project
      const { data: feedback } = await db
        .from('feedback')
        .select('*')
        .eq('project_id', project.id)
        .order('created_at', { ascending: false })
        .limit(5);

      let response = `# ${project.name}\n\n`;
      response += `- Status: ${project.status}\n`;
      response += `- Type: ${project.type || 'Not specified'}\n`;
      response += `- Word count: ${project.word_count || 0}\n`;
      response += `- Created: ${project.created_at?.slice(0, 10)}\n`;
      response += `- Last updated: ${project.updated_at?.slice(0, 10)}\n`;

      if (project.description) {
        response += `\n## Description\n${project.description}\n`;
      }

      if (project.notes) {
        response += `\n## Notes\n${project.notes}\n`;
      }

      if (project.key_decisions?.length > 0) {
        response += `\n## Key Decisions\n`;
        for (const d of project.key_decisions) {
          response += `- ${d}\n`;
        }
      }

      if (feedback?.length > 0) {
        response += `\n## Recent Feedback\n`;
        for (const f of feedback) {
          response += `- [${f.source}] ${f.feedback.slice(0, 100)}${f.feedback.length > 100 ? '...' : ''}\n`;
        }
      }

      return { content: [{ type: 'text', text: response }] };
    }

    case 'memory_update_project': {
      const { data: existing } = await db
        .from('projects')
        .select('*')
        .ilike('name', `%${args.project_name}%`)
        .single();

      if (!existing) {
        return {
          content: [
            { type: 'text', text: `Project "${args.project_name}" not found.` },
          ],
        };
      }

      const updates = {
        updated_at: new Date().toISOString(),
      };

      if (args.status) updates.status = args.status;
      if (args.word_count) updates.word_count = args.word_count;
      if (args.current_draft_id) updates.current_draft_id = args.current_draft_id;
      if (args.notes) updates.notes = args.notes;

      await db.from('projects').update(updates).eq('id', existing.id);

      return {
        content: [
          {
            type: 'text',
            text: `Updated "${existing.name}": ${Object.keys(updates).filter(k => k !== 'updated_at').join(', ')}`,
          },
        ],
      };
    }

    case 'memory_create_project': {
      const { data: project, error } = await db
        .from('projects')
        .insert({
          name: args.name,
          description: args.description,
          type: args.type || 'other',
          status: 'idea',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        })
        .select()
        .single();

      if (error) {
        throw new Error(`Failed to create project: ${error.message}`);
      }

      return {
        content: [
          {
            type: 'text',
            text: `Created project "${args.name}" (${args.type || 'other'})`,
          },
        ],
      };
    }

    case 'memory_list_projects': {
      let query = db.from('projects').select('*');

      if (args.status && args.status !== 'all') {
        query = query.eq('status', args.status);
      }

      const { data: projects } = await query.order('updated_at', {
        ascending: false,
      });

      if (!projects?.length) {
        return {
          content: [{ type: 'text', text: 'No projects found.' }],
        };
      }

      let response = '# Projects\n\n';
      for (const p of projects) {
        response += `## ${p.name}\n`;
        response += `- Status: ${p.status}\n`;
        response += `- Words: ${p.word_count || 0}\n`;
        response += `- Updated: ${p.updated_at?.slice(0, 10)}\n\n`;
      }

      return { content: [{ type: 'text', text: response }] };
    }

    case 'memory_record_lesson': {
      const { data, error } = await db
        .from('creative_memory')
        .insert({
          content: args.lesson,
          category: args.category,
          worked: args.worked,
          project_name: args.project_name,
          created_at: new Date().toISOString(),
        })
        .select()
        .single();

      if (error) {
        throw new Error(`Failed to record lesson: ${error.message}`);
      }

      return {
        content: [
          {
            type: 'text',
            text: `Recorded lesson [${args.category}]: "${args.lesson}" (${args.worked ? 'worked' : 'did not work'})`,
          },
        ],
      };
    }

    case 'memory_get_lessons': {
      let query = db.from('creative_memory').select('*');

      if (args.category && args.category !== 'all') {
        query = query.eq('category', args.category);
      }

      if (args.worked_only) {
        query = query.eq('worked', true);
      }

      const { data: lessons } = await query.order('created_at', {
        ascending: false,
      });

      if (!lessons?.length) {
        return {
          content: [{ type: 'text', text: 'No lessons recorded yet.' }],
        };
      }

      let response = '# Creative Lessons\n\n';

      // Group by category
      const byCategory = {};
      for (const l of lessons) {
        if (!byCategory[l.category]) byCategory[l.category] = [];
        byCategory[l.category].push(l);
      }

      for (const [cat, items] of Object.entries(byCategory)) {
        response += `## ${cat.charAt(0).toUpperCase() + cat.slice(1)}\n`;
        for (const l of items) {
          const icon = l.worked ? '✓' : '✗';
          response += `- ${icon} ${l.content}\n`;
        }
        response += '\n';
      }

      return { content: [{ type: 'text', text: response }] };
    }

    case 'memory_record_feedback': {
      // Find project
      const { data: project } = await db
        .from('projects')
        .select('id')
        .ilike('name', `%${args.project_name}%`)
        .single();

      const { error } = await db.from('feedback').insert({
        project_id: project?.id,
        project_name: args.project_name,
        source: args.source,
        feedback: args.feedback,
        acted_on: args.acted_on || false,
        created_at: new Date().toISOString(),
      });

      if (error) {
        throw new Error(`Failed to record feedback: ${error.message}`);
      }

      return {
        content: [
          {
            type: 'text',
            text: `Recorded feedback from ${args.source} on "${args.project_name}"`,
          },
        ],
      };
    }

    case 'memory_search': {
      // Search across tables
      const results = [];

      // Search projects
      const { data: projects } = await db
        .from('projects')
        .select('*')
        .or(`name.ilike.%${args.query}%,description.ilike.%${args.query}%,notes.ilike.%${args.query}%`);

      if (projects?.length) {
        results.push(
          ...projects.map((p) => ({
            type: 'project',
            name: p.name,
            match: p.description || p.notes,
          }))
        );
      }

      // Search lessons
      const { data: lessons } = await db
        .from('creative_memory')
        .select('*')
        .ilike('content', `%${args.query}%`);

      if (lessons?.length) {
        results.push(
          ...lessons.map((l) => ({
            type: 'lesson',
            category: l.category,
            match: l.content,
          }))
        );
      }

      // Search sessions
      const { data: sessions } = await db
        .from('sessions')
        .select('*')
        .ilike('summary', `%${args.query}%`);

      if (sessions?.length) {
        results.push(
          ...sessions.map((s) => ({
            type: 'session',
            date: s.ended_at?.slice(0, 10),
            match: s.summary,
          }))
        );
      }

      if (results.length === 0) {
        return {
          content: [
            { type: 'text', text: `No results found for "${args.query}"` },
          ],
        };
      }

      let response = `# Search Results for "${args.query}"\n\n`;
      for (const r of results) {
        response += `- [${r.type}] ${r.name || r.category || r.date}: ${r.match?.slice(0, 100)}...\n`;
      }

      return { content: [{ type: 'text', text: response }] };
    }

    default:
      throw new Error(`Unknown memory tool: ${name}`);
  }
}
