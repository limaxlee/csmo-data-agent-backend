// Request and response shapes for /api/threads and /api/threads/{id}/messages.

export interface Thread {
  id: string;
  agent_thread_id: string;
  title: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ThreadListResponse {
  threads: Thread[];
  total: number;
}

export interface Message {
  id: string;
  role: string;
  content: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface MessageListResponse {
  messages: Message[];
  total: number;
}
