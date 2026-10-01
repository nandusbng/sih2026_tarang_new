import re

with open('sonar-analyst.html', 'r') as f:
    content = f.read()

# Replace the articles container with an empty one containing an ID
new_container = '<div class="flex flex-col gap-space-md" id="anomalies-container">'
# The container starts exactly at: <div class="flex flex-col gap-space-md">
# and ends right before <!-- RIGHT 28% COLUMN...

# We'll use a regex to replace everything from <!-- CARD 1: to </article> (the last one)
pattern = re.compile(r'<!-- CARD 1:.*?</article>', re.DOTALL)
content = pattern.sub('', content)

# Add the ID to the container
content = content.replace('<div class="flex flex-col gap-space-md">', '<div class="flex flex-col gap-space-md" id="anomalies-container">', 1)

# Add the Supabase JS logic at the bottom before </script>
supabase_js = """
    // --- Supabase Integration ---
    const supabaseUrl = 'https://cryfgdedvnyczhausidk.supabase.co';
    const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNyeWZnZGVkdm55Y3poYXVzaWRrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODk0MDA1NzEsImV4cCI6MjEwNDk3NjU3MX0.ldityW-EB_Nn4iZ5f116CzPHFGIovksyz2uz23LVw8o';
    const supabaseClient = window.supabase.createClient(supabaseUrl, supabaseKey);

    async function fetchLatestDispatch() {
        const { data, error } = await supabaseClient
            .from('dispatches')
            .select('payload')
            .eq('payload->>destination', 'SONAR_ANALYST')
            .order('created_at', { ascending: false })
            .limit(1);

        if (error) {
            console.error('Error fetching dispatch:', error);
            return;
        }

        if (data && data.length > 0) {
            renderAnomalies(data[0].payload.detections || []);
        } else {
            document.getElementById('anomalies-container').innerHTML = '<p class="text-on-surface-variant p-4">No pending Class C verifications.</p>';
        }
    }

    function renderAnomalies(detections) {
        const container = document.getElementById('anomalies-container');
        if (!detections || detections.length === 0) {
            container.innerHTML = '<p class="text-on-surface-variant p-4">No pending Class C verifications.</p>';
            return;
        }

        let html = '';
        detections.forEach((det, idx) => {
            html += `
            <article class="p-space-lg rounded-xl bg-surface-container-lowest shadow-none hover:shadow-sm border border-border-subtle transition-all flex flex-col gap-space-md group" id="anomaly-${det.id.toLowerCase()}">
                <div class="flex flex-wrap items-center justify-between gap-space-sm">
                    <div class="flex items-center gap-2">
                        <span class="px-2.5 py-1 rounded-md bg-surface-container-low text-abyssal-navy font-label-code text-label-code tracking-widest font-bold">TARGET #${det.id}</span>
                        <span class="font-label-code text-label-code text-on-surface-variant">SUBBASIN: UNKNOWN</span>
                        <span class="px-2 py-0.5 rounded-full bg-sonar-alert/10 text-sonar-alert font-label-code text-label-code font-bold">MANUAL REVIEW REQ</span>
                    </div>
                    <div class="flex items-center gap-1.5 px-3 py-1 rounded-full bg-surface-ice text-abyssal-navy">
                        <span class="material-symbols-outlined text-seafoam-glow text-[16px]">verified</span>
                        <span class="font-label-code text-label-code font-bold">${det.confidence}% AI CONFIDENCE</span>
                    </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-12 gap-space-md">
                    <div class="md:col-span-6 flex flex-col gap-2">
                        <div class="relative w-full h-52 rounded-lg overflow-hidden bg-abyssal-navy">
                            <img src="${det.crop_url}" class="w-full h-full object-cover opacity-90 group-hover:scale-105 transition-transform duration-500" alt="Detection Crop">
                        </div>
                    </div>
                    
                    <div class="md:col-span-6 flex flex-col justify-between">
                        <div class="space-y-space-sm">
                            <div>
                                <h3 class="font-headline-sm text-headline-sm text-abyssal-navy font-bold">${det.title || det.class_name || 'Unknown Detection'}</h3>
                                <p class="font-body-sm text-body-sm text-on-surface-variant mt-1">Class C detection requires expert verification before Coast Guard escalation.</p>
                            </div>
                            <div class="grid grid-cols-2 gap-2 p-3 rounded-xl bg-surface-ice">
                                <div>
                                    <span class="font-label-code text-[10px] text-on-surface-variant uppercase block">Material</span>
                                    <span class="font-telemetry-metric text-telemetry-metric text-abyssal-navy font-bold leading-none">${det.material || 'N/A'}</span>
                                </div>
                                <div>
                                    <span class="font-label-code text-[10px] text-on-surface-variant uppercase block">Depth/Dim</span>
                                    <span class="font-telemetry-metric text-telemetry-metric text-abyssal-navy font-bold leading-none">Z: ${det.depth || 'N/A'}</span>
                                </div>
                            </div>
                        </div>
                        
                        <div class="flex items-center gap-2 pt-space-sm mt-space-xs border-t border-border-subtle/50">
                            <button class="flex-1 flex items-center justify-center gap-2 py-2.5 px-space-md rounded-xl bg-seafoam-glow text-abyssal-navy font-body-sm text-body-sm font-bold shadow-md hover:bg-seafoam-glow/90 transition-all" onclick="handleAccept('${det.id}')">
                                <span class="material-symbols-outlined text-[18px]">check_circle</span>
                                <span>Accept Verification</span>
                            </button>
                            <button class="flex items-center justify-center p-2.5 rounded-xl bg-surface-ice hover:bg-sonar-alert hover:text-white transition-colors" onclick="handleReject('${det.id}', 'False Positive')">
                                <span class="material-symbols-outlined text-[18px]">close</span>
                            </button>
                        </div>
                    </div>
                </div>
            </article>
            `;
        });
        container.innerHTML = html;
    }

    // Initial fetch
    fetchLatestDispatch();

    // Subscribe to real-time inserts
    supabaseClient
        .channel('sonar_dispatches_channel')
        .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'dispatches' }, payload => {
            const newDispatch = payload.new.payload;
            if (newDispatch && newDispatch.destination === 'SONAR_ANALYST') {
                console.log('New Class C dispatch received via Supabase Realtime!', newDispatch);
                renderAnomalies(newDispatch.detections || []);
            }
        })
        .subscribe();
</script>
"""

content = content.replace('</script>\n</div></main>', supabase_js + '\n</div></main>')

with open('sonar-analyst.html', 'w') as f:
    f.write(content)

