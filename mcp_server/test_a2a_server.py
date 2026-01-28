"""
Minimal A2A Test Server for Chamba
Run with: python test_a2a_server.py
"""
import sys
sys.path.insert(0, '.')

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from a2a.agent_card import router as a2a_router

app = FastAPI(title='Chamba A2A Test Server')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*']
)
app.include_router(a2a_router)

@app.get('/health')
async def health():
    return {'status': 'ok', 'server': 'test-a2a'}

@app.get('/')
async def root():
    return {
        'message': 'Chamba A2A Test Server',
        'endpoints': [
            '/.well-known/agent.json',
            '/v1/card',
            '/discovery/agents'
        ]
    }

if __name__ == "__main__":
    import uvicorn
    print("Starting Chamba A2A Test Server on http://localhost:8001")
    uvicorn.run(app, host='0.0.0.0', port=8001)
