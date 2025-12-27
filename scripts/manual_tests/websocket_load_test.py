#!/usr/bin/env python3
import argparse
import asyncio
import json
import logging
import random
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

@dataclass
class LoadTestResult:
    clients_connected: int = 0
    clients_failed: int = 0
    events_sent: int = 0
    events_received: int = 0
    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    duration_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self):
        throughput = self.events_received / self.duration_seconds if self.duration_seconds > 0 else 0
        return {
            "clients_connected": self.clients_connected,
            "events_sent": self.events_sent,
            "events_received": self.events_received,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "throughput": round(throughput, 2),
        }

class WebSocketLoadTester:
    def __init__(self, ws_url="ws://localhost:4200/ws", num_clients=10, duration=30, events_per_sec=5):
        self.ws_url = ws_url
        self.num_clients = num_clients
        self.duration = duration
        self.events_per_sec = events_per_sec
        self.result = LoadTestResult()
        self.latencies = []
    
    async def run_test(self):
        if not HAS_AIOHTTP:
            self.result.errors.append("aiohttp not installed")
            return self.result
        
        logger.info(f"Starting: {self.num_clients} clients, {self.duration}s")
        start = time.time()
        
        tasks = [asyncio.create_task(self._run_client(i)) for i in range(self.num_clients)]
        sender = asyncio.create_task(self._send_events())
        
        await asyncio.sleep(self.duration)
        
        sender.cancel()
        for t in tasks:
            t.cancel()
        
        self.result.duration_seconds = time.time() - start
        if self.latencies:
            self.result.avg_latency_ms = sum(self.latencies) / len(self.latencies)
            self.result.max_latency_ms = max(self.latencies)
        
        return self.result
    
    async def _run_client(self, client_id):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(self.ws_url, timeout=10) as ws:
                    self.result.clients_connected += 1
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            self.result.events_received += 1
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.result.clients_failed += 1
    
    async def _send_events(self):
        import urllib.request
        url = self.ws_url.replace("ws://", "http://").replace("/ws", "/events")
        interval = 1.0 / self.events_per_sec
        
        while True:
            try:
                event = {"timestamp": datetime.now().isoformat(), "event_type": "load_test", "agent_name": "tester"}
                data = json.dumps(event).encode()
                req = urllib.request.Request(url, data=data, method="POST")
                req.add_header("Content-Type", "application/json")
                with urllib.request.urlopen(req, timeout=5) as r:
                    if r.status == 200:
                        self.result.events_sent += 1
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except:
                await asyncio.sleep(interval)
    
    def print_results(self):
        r = self.result.to_dict()
        print(f"Results: {r["clients_connected"]} clients, {r["events_sent"]} sent, {r["events_received"]} received")
        print(f"Throughput: {r["throughput"]} events/sec")

def main():
    parser = argparse.ArgumentParser(description="WebSocket load test")
    parser.add_argument("--clients", type=int, default=10)
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--events-per-sec", type=int, default=5)
    parser.add_argument("--dashboard-url", default="ws://localhost:4200/ws")
    parser.add_argument("--output", "-o", type=str)
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--quiet", "-q", action="store_true")
    args = parser.parse_args()
    
    if args.quiet: logger.setLevel(logging.ERROR)
    elif args.verbose: logger.setLevel(logging.DEBUG)
    
    print(f"WebSocket Load Test: {args.clients} clients, {args.duration}s")
    print("=" * 50)
    
    tester = WebSocketLoadTester(args.dashboard_url, args.clients, args.duration, args.events_per_sec)
    result = asyncio.run(tester.run_test())
    tester.print_results()
    
    if args.output:
        Path(args.output).write_text(json.dumps(result.to_dict(), indent=2))
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
