const { createClient } = require('@supabase/supabase-js');
const supabaseUrl = 'https://cryfgdedvnyczhausidk.supabase.co';
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNyeWZnZGVkdm55Y3poYXVzaWRrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODk0MDA1NzEsImV4cCI6MjEwNDk3NjU3MX0.ldityW-EB_Nn4iZ5f116CzPHFGIovksyz2uz23LVw8o';
const supabase = createClient(supabaseUrl, supabaseKey);

async function test() {
    const { data, error } = await supabase
        .from('dispatches')
        .select('payload')
        .eq('payload->>destination', 'SONAR_ANALYST')
        .order('created_at', { ascending: false })
        .limit(1);
    console.log("TEST 1 - eq ->>", data, error);
    
    const { data: data2, error: error2 } = await supabase
        .from('dispatches')
        .select('payload')
        .contains('payload', { destination: 'SONAR_ANALYST' })
        .order('created_at', { ascending: false })
        .limit(1);
    console.log("TEST 2 - contains", data2 ? data2.length : 0, error2);
}
test();
