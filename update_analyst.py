import re

with open('marine-analyst.html', 'r') as f:
    content = f.read()

# 1. Update Card Object Number
content = re.sub(
    r'WP-\$\{\(idx\+1\)\.toString\(\)\.padStart\(2, \'0\'\)\} · \$\{det\.id\}',
    r'${idx+1} · ${det.id}',
    content
)

# 2. Update Map Marker
content = content.replace(
    'WP-${markerIndex}',
    '${parseInt(markerIndex)}'
)

# 3. Replace kMeans function with DBSCAN function
kmeans_pattern = r'// Simple K-Means implementation.*?return clusters\.filter\(c => c\.points\.length > 0\);\s*\}'
dbscan_code = """// Simple DBSCAN implementation
      function dbscan(points, eps, minPts) {
          let clusters = [];
          let visited = new Set();
          let noise = [];
          
          function regionQuery(p) {
              return points.filter(q => {
                  let d = map.distance([p.lat, p.lon], [q.lat, q.lon]);
                  return d <= eps;
              });
          }
          
          points.forEach(p => {
              if (visited.has(p)) return;
              visited.add(p);
              let neighbors = regionQuery(p);
              
              if (neighbors.length < minPts) {
                  noise.push(p);
              } else {
                  let cluster = { points: [] };
                  clusters.push(cluster);
                  
                  let i = 0;
                  while (i < neighbors.length) {
                      let q = neighbors[i];
                      if (!visited.has(q)) {
                          visited.add(q);
                          let qNeighbors = regionQuery(q);
                          if (qNeighbors.length >= minPts) {
                              // avoid duplicates
                              qNeighbors.forEach(qn => {
                                  if(!neighbors.includes(qn)) neighbors.push(qn);
                              });
                          }
                      }
                      
                      let inCluster = clusters.some(c => c.points.includes(q));
                      if (!inCluster) {
                          cluster.points.push(q);
                      }
                      i++;
                  }
              }
          });
          
          // Calculate centroids
          clusters.forEach(c => {
              let sumLat = 0, sumLon = 0;
              c.points.forEach(p => { sumLat += p.lat; sumLon += p.lon; });
              c.centroid = { lat: sumLat / c.points.length, lon: sumLon / c.points.length };
          });
          
          return {clusters, noise};
      }"""

content = re.sub(kmeans_pattern, dbscan_code, content, flags=re.DOTALL)

# 4. Update the calling code from kMeans to DBSCAN
kmeans_call = r'// Run Clustering.*?let clusters = kMeans\(allMapPoints, k\);'
dbscan_call = """// Run DBSCAN Clustering Simulation (eps: 80km, minPts: 1 for demo purposes)
              let {clusters, noise} = dbscan(allMapPoints, 80000, 1);"""
content = re.sub(kmeans_call, dbscan_call, content, flags=re.DOTALL)

with open('marine-analyst.html', 'w') as f:
    f.write(content)

print("Updated marine-analyst.html successfully")
