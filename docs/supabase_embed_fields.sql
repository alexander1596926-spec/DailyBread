alter table if exists public.embeds
  add column if not exists message_content text,
  add column if not exists image_url text;
