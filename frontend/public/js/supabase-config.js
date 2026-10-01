import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js/+esm';

const SUPABASE_URL = 'https://cryfgdedvnyczhausidk.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNyeWZnZGVkdm55Y3poYXVzaWRrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODk0MDA1NzEsImV4cCI6MjEwNDk3NjU3MX0.ldityW-EB_Nn4iZ5f116CzPHFGIovksyz2uz23LVw8o';

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
console.log("Supabase initialized successfully.");
