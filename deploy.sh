# Copy static files to local build
rsync -avh --delete static/ /another/site/fractal-of-insight/static/

cd /another/site/fractal-of-insight/

# Deploy to hosted server
rsync -av --checksum --delete -e ssh ./ a2:fractal-of-insight.mduo13.com/

