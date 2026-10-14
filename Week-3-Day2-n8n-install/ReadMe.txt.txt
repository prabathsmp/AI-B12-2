# Download and install node js 
node --version
npm --version

# Option A - run it without installing
npx n8n
# Option B - install it properly
npm install -g n8n
n8n start
# Option C - Docker
docker run -it --rm -p 5678:5678 \
  -v n8n_data:/home/node/.n8n docker.n8n.io/n8nio/n8n

npx n8n
Editor is now accessible via:
http://localhost:5678
[browser] n8n editor open, owner account created,
          test workflow executed with a green tick