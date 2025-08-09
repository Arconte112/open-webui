import { WEBUI_API_BASE_URL } from '$lib/constants';

export const getExternalMemories = async (token: string) => {
  const res = await fetch(`${WEBUI_API_BASE_URL}/soren/external-memories`, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
  if (!res.ok) throw new Error(await res.text());
  const data = await res.json();
  return (data?.memories || []).map((m: any) => ({
    id: m.id,
    content: m.content,
    importance: m.importance,
    tags: m.tags,
    metadata: m.metadata,
    updated_at_epoch: m.updated_at_epoch,
    updated_at: m.updated_at
  }));
};

export const addExternalMemory = async (
  token: string,
  content: string,
  importance: number,
  tags: string[],
  metadata: any
) => {
  const res = await fetch(`${WEBUI_API_BASE_URL}/soren/external-memories`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({ content, importance, tags, metadata })
  });
  if (!res.ok) throw new Error(await res.text());
  return await res.json();
};

export const updateExternalMemory = async (
  token: string,
  id: number,
  content?: string,
  importance?: number,
  tags?: string[],
  metadata?: any
) => {
  const res = await fetch(`${WEBUI_API_BASE_URL}/soren/external-memories/${id}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({ content, importance, tags, metadata })
  });
  if (!res.ok) throw new Error(await res.text());
  return await res.json();
};

export const deleteExternalMemory = async (token: string, id: number) => {
  const res = await fetch(`${WEBUI_API_BASE_URL}/soren/external-memories/${id}`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
  if (!res.ok) throw new Error(await res.text());
  return await res.json();
};

export const clearExternalMemories = async (token: string) => {
  const res = await fetch(`${WEBUI_API_BASE_URL}/soren/external-memories`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
  if (!res.ok) throw new Error(await res.text());
  return await res.json();
};

