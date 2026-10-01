const { createClient } = require('@supabase/supabase-js');
const supabaseUrl = 'https://cryfgdedvnyczhausidk.supabase.co';
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNyeWZnZGVkdm55Y3poYXVzaWRrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODk0MDA1NzEsImV4cCI6MjEwNDk3NjU3MX0.ldityW-EB_Nn4iZ5f116CzPHFGIovksyz2uz23LVw8o';
const supabase = createClient(supabaseUrl, supabaseKey);
async function test() {
    const { data } = await supabase.from('dispatches').select('*').order('created_at', { ascending: false }).limit(2);
    console.log(JSON.stringify(data, null, 2));
}
test();
