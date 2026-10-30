import json, random, time

def process_data(data):
    result = []
    for item in data:
        if item.get("type") == "user":
            result.append({
                "id": item["id"],
                "score": random.randint(0, 100),
                "timestamp": time.time()
            })
    return json.dumps(result)

def validate_config(cfg):
    required = ["host", "port", "api_key"]
    for key in required:
        if key not in cfg:
            return False
    return True

class MockServer:
    def __init__(self, port=8080):
        self.port = port
        self.routes = {}
    
    def register(self, path, handler):
        self.routes[path] = handler
    
    def handle(self, request):
        if request["path"] in self.routes:
            return self.routes[request["path"]](request)
        return {"error": "not found"}

if __name__ == "__main__":
    server = MockServer()
    server.register("/health", lambda r: {"status": "ok"})
    print(process_data([{"type": "user", "id": 1}]))
