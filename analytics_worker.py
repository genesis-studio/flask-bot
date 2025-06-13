import asyncio
import aiohttp
import os
import time
from typing import List, Dict, Any, Optional
import json
from dataclasses import dataclass

# Constants
BASE_URL = "https://genesistudio.com"
VIEWER_BASE_URL = f"{BASE_URL}/viewer"

# Feature flags
ENABLE_ORPHANED_INSIGHTS_CLEANUP = False
ENABLE_WEEKLY_UPDATES = False  # Toggle for weekly insights
MAX_CONCURRENT_REQUESTS = 5  # Limit concurrent PostHog requests
BATCH_SIZE = 10  # Process novels in batches

@dataclass
class Novel:
    id: str
    abbreviation: str
    insight_id: Optional[str]
    insight_id_weekly: Optional[str]
    novel_title: str
    total_views: Optional[int]
    page_views: Optional[int]
    status: str
    serialization: Optional[str]

@dataclass
class Chapter:
    id: str
    novel: str

class AnalyticsWorker:
    def __init__(self):
        self.supabase_url = os.environ.get('SUPABASE_URL')
        self.supabase_anon_key = os.environ.get('PUBLIC_SUPABASE_ANON_KEY')
        self.posthog_api_key = os.environ.get('POSTHOG_API_KEY')
        self.posthog_project_id = os.environ.get('POSTHOG_PROJECT_ID')
        
        if not all([self.supabase_url, self.supabase_anon_key, self.posthog_api_key, self.posthog_project_id]):
            raise ValueError("Missing required environment variables")

    async def run_analytics(self):
        """Main function that replicates the Deno analytics function"""
        print("[MAIN] Starting analytics worker...")
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                # Fetch all data in parallel
                print("[MAIN] Fetching novels and chapters in parallel...")
                novels_data, chapters_data = await asyncio.gather(
                    self.fetch_novels(session),
                    self.fetch_chapters(session)
                )
                
                novels = [Novel(**novel) for novel in novels_data]
                chapters = [Chapter(**chapter) for chapter in chapters_data]
                
                print(f"[MAIN] Fetched {len(novels)} novels and {len(chapters)} chapters")
                
                # Create efficient lookup for chapters by novel
                chapters_by_novel = {}
                for chapter in chapters:
                    if chapter.novel not in chapters_by_novel:
                        chapters_by_novel[chapter.novel] = []
                    chapters_by_novel[chapter.novel].append(chapter.id)
                
                # Filter novels that need processing
                valid_novels = [novel for novel in novels if novel.abbreviation]
                print(f"[MAIN] Processing {len(valid_novels)} valid novels")
                
                # Process novels in batches with concurrency control
                results = await self.process_batched_novels(valid_novels, chapters_by_novel, session)
                
                # Update rankings
                print("[MAIN] Updating rankings...")
                await self.update_rankings(session)
                
                # Cleanup orphaned insights if enabled
                if ENABLE_ORPHANED_INSIGHTS_CLEANUP:
                    print("[MAIN] Cleaning up orphaned insights...")
                    await self.cleanup_orphaned_insights(session)
                
                execution_time = (time.time() - start_time) * 1000
                print(f"[MAIN] Processing completed in {execution_time:.0f}ms")
                
                return {
                    "success": True,
                    "processed": len(valid_novels),
                    "executionTime": f"{execution_time:.0f}ms",
                    "weeklyUpdatesEnabled": ENABLE_WEEKLY_UPDATES
                }
                
        except Exception as error:
            print(f"[MAIN] Error: {str(error)}")
            return {"error": str(error)}

    async def fetch_novels(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Fetch novels from Supabase"""
        url = f"{self.supabase_url}rest/v1/novels"
        headers = {
            'Authorization': f'Bearer {self.supabase_anon_key}',
            'apikey': self.supabase_anon_key,
            'Content-Type': 'application/json'
        }
        params = {
            'select': 'id,abbreviation,insight_id,insight_id_weekly,novel_title,total_views,page_views,status,serialization',
            'status': 'eq.published'
        }
        
        async with session.get(url, headers=headers, params=params) as response:
            if response.status != 200:
                raise Exception(f"Error fetching novels: {response.status}")
            return await response.json()

    async def fetch_chapters(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Fetch chapters from Supabase"""
        url = f"{self.supabase_url}rest/v1/chapters"
        headers = {
            'Authorization': f'Bearer {self.supabase_anon_key}',
            'apikey': self.supabase_anon_key,
            'Content-Type': 'application/json'
        }
        params = {
            'select': 'id,novel',
            'status': 'eq.released'
        }
        
        async with session.get(url, headers=headers, params=params) as response:
            if response.status != 200:
                raise Exception(f"Error fetching chapters: {response.status}")
            return await response.json()

    async def process_batched_novels(self, novels: List[Novel], chapters_by_novel: Dict, session: aiohttp.ClientSession):
        """Process novels in batches with concurrency control"""
        results = []
        for i in range(0, len(novels), BATCH_SIZE):
            batch = novels[i:i + BATCH_SIZE]
            print(f"[BATCH] Processing batch {i // BATCH_SIZE + 1}/{(len(novels) + BATCH_SIZE - 1) // BATCH_SIZE}")
            
            batch_tasks = [self.process_novel(novel, chapters_by_novel, session) for novel in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            results.extend(batch_results)
        
        return results

    async def process_novel(self, novel: Novel, chapters_by_novel: Dict, session: aiohttp.ClientSession):
        """Process individual novel with optimized parallel operations"""
        novel_chapters = chapters_by_novel.get(novel.id, [])
        print(f"[NOVEL] Processing {novel.novel_title} ({len(novel_chapters)} chapters)")
        
        try:
            # Prepare insight creation tasks
            tasks = []
            
            # Overall insight
            if not novel.insight_id:
                tasks.append({
                    'type': 'overall',
                    'task': self.create_insight(novel, novel_chapters, 'Page Views', 'all', 'week', session)
                })
            
            # Weekly insight (only if enabled)
            if ENABLE_WEEKLY_UPDATES and not novel.insight_id_weekly:
                tasks.append({
                    'type': 'weekly',
                    'task': self.create_insight(novel, novel_chapters, 'Weekly Page Views (7-day)', '-7d', 'day', session)
                })
            
            # Execute insight creation with concurrency limit
            created_insights = await self.execute_with_concurrency_limit(tasks, MAX_CONCURRENT_REQUESTS)
            
            # Update novel with new insight IDs
            updates = {}
            for result in created_insights:
                if result.get('status') == 'fulfilled' and result.get('value', {}).get('insightId'):
                    if result['value']['type'] == 'overall':
                        updates['insight_id'] = result['value']['insightId']
                    elif result['value']['type'] == 'weekly':
                        updates['insight_id_weekly'] = result['value']['insightId']
            
            if updates:
                await self.update_novel(novel.id, updates, session)
            
            # Fetch insight data for existing insights
            fetch_tasks = []
            if novel.insight_id or updates.get('insight_id'):
                insight_id = updates.get('insight_id') or novel.insight_id
                fetch_tasks.append({
                    'type': 'overall',
                    'task': self.fetch_insight_data(insight_id, novel.id, 'overall', session)
                })
            
            if ENABLE_WEEKLY_UPDATES and (novel.insight_id_weekly or updates.get('insight_id_weekly')):
                weekly_insight_id = updates.get('insight_id_weekly') or novel.insight_id_weekly
                fetch_tasks.append({
                    'type': 'weekly',
                    'task': self.fetch_insight_data(weekly_insight_id, novel.id, 'weekly', session)
                })
            
            # Fetch insight data with concurrency control
            if fetch_tasks:
                insight_results = await self.execute_with_concurrency_limit(fetch_tasks, MAX_CONCURRENT_REQUESTS)
                
                # Process results and update novel views
                novel_updates = {}
                for result in insight_results:
                    print(f"[NOVEL] Result: {result}")
                    if result.get('status') == 'fulfilled' and result.get('value', {}).get('data', {}).get('trend'):
                        total_views = self.calculate_total_views(result['value']['data']['trend'])
                        if result['value']['type'] == 'overall':
                            novel_updates['total_views'] = total_views
                        elif result['value']['type'] == 'weekly':
                            novel_updates['page_views'] = total_views
                
                if novel_updates:
                    await self.update_novel(novel.id, novel_updates, session)
            
            return {"success": True, "novel": novel.id}
            
        except Exception as error:
            print(f"[NOVEL] Error processing {novel.novel_title}: {str(error)}")
            return {"success": False, "novel": novel.id, "error": str(error)}

    async def execute_with_concurrency_limit(self, tasks: List[Dict], limit: int):
        """Execute promises with concurrency limit"""
        results = []
        for i in range(0, len(tasks), limit):
            batch = tasks[i:i + limit]
            batch_results = []
            
            for task in batch:
                try:
                    result = await task['task']
                    batch_results.append({
                        'status': 'fulfilled',
                        'value': {**result, 'type': task['type']} if result else None
                    })
                except Exception as error:
                    batch_results.append({
                        'status': 'rejected',
                        'reason': str(error),
                        'type': task['type']
                    })
            
            results.extend(batch_results)
        
        return results

    def calculate_total_views(self, trend_data: List[Dict]) -> int:
        """Calculate total views from trend data"""
        return sum(item.get('pageviews', 0) for item in trend_data)

    async def create_insight(self, novel: Novel, chapter_ids: List[str], name_suffix: str, date_from: str, interval: str, session: aiohttp.ClientSession):
        """Create PostHog insight"""
        print(f"[CREATE_INSIGHT] Creating {name_suffix} for {novel.novel_title}")
        
        try:
            url_patterns = [
                f"{BASE_URL}/novel/{novel.abbreviation}",
                *[f"{VIEWER_BASE_URL}/{chapter_id}" for chapter_id in chapter_ids]
            ]
            
            insight_data = {
                "name": f"{novel.novel_title or novel.abbreviation} {name_suffix}",
                "query": {
                    "kind": "InsightVizNode",
                    "source": {
                        "kind": "TrendsQuery",
                        "properties": {
                            "type": "OR",
                            "values": [
                                {
                                    "type": "AND",
                                    "values": [
                                        {
                                            "key": "$current_url",
                                            "type": "event",
                                            "value": url,
                                            "operator": "exact"
                                        }
                                    ]
                                } for url in url_patterns
                            ]
                        },
                        "dateRange": {"date_from": date_from},
                        "series": [
                            {
                                "kind": "EventsNode",
                                "event": "$pageview",
                                "name": "$pageview",
                                "math": "total"
                            }
                        ],
                        "interval": interval,
                        "breakdownFilter": {
                            "breakdown_type": "event",
                            "breakdown": "$current_url",
                            "breakdown_limit": 1000
                        },
                        "trendsFilter": {"display": "ActionsLineGraph"}
                    },
                    "full": True
                },
                "saved": True
            }
            
            headers = {
                'Authorization': f'Bearer {self.posthog_api_key}',
                'Content-Type': 'application/json'
            }
            
            async with session.post(
                f'https://app.posthog.com/api/projects/{self.posthog_project_id}/insights/',
                headers=headers,
                json=insight_data
            ) as response:
                if response.status != 200 and response.status != 201:
                    error_text = await response.text()
                    raise Exception(f"Failed to create insight: {response.status} {error_text}")
                
                data = await response.json()
                return {"insightId": data.get("short_id")}
                
        except Exception as error:
            print(f"[CREATE_INSIGHT] Error: {str(error)}")
            return None

    async def fetch_insight_data(self, insight_id: str, novel_id: str, insight_type: str, session: aiohttp.ClientSession):
        """Fetch insight data from PostHog"""
        print(f"[FETCH_INSIGHT] Fetching {insight_type} data for novel {novel_id} with insight id {insight_id}")
        
        try:
            headers = {
                'Authorization': f'Bearer {self.posthog_api_key}',
                'Content-Type': 'application/json'
            }
            
            
            print("Going to fetch insight data: ", f'https://app.posthog.com/api/projects/{self.posthog_project_id}/insights/?short_id={insight_id}&refresh=force_blocking')
            async with session.get(
                f'https://app.posthog.com/api/projects/{self.posthog_project_id}/insights/?short_id={insight_id}&refresh=force_blocking',
                headers=headers
            ) as response:
                if response.status != 200:
                    raise Exception(f"Failed to fetch insight: {response.status}")
                
                data = await response.json()
                result = data.get('results', [{}])[0] if data.get('results') else {}
                
                trend_data = None
                if result.get('result'):
                    trend_data = [
                        {
                            'url': item.get('label'),
                            'pageviews': item.get('count', 0),
                            'data': item.get('data', []),
                            'labels': item.get('days') or item.get('labels', [])
                        } for item in result['result']
                    ]
                elif result.get('query_result', {}).get('result'):
                    trend_data = [
                        {
                            'url': item.get('label'),
                            'pageviews': item.get('count', 0),
                            'data': item.get('data', []),
                            'labels': item.get('days') or item.get('labels', [])
                        } for item in result['query_result']['result']
                    ]
                
                return {"data": {"trend": trend_data}} if trend_data else None
                
        except Exception as error:
            print(f"[FETCH_INSIGHT] Error: {str(error)}")
            return None

    async def update_novel(self, novel_id: str, updates: Dict, session: aiohttp.ClientSession):
        """Update novel in Supabase"""
        url = f"{self.supabase_url}rest/v1/novels"
        headers = {
            'Authorization': f'Bearer {self.supabase_anon_key}',
            'apikey': self.supabase_anon_key,
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal'
        }
        params = {'id': f'eq.{novel_id}'}
        
        async with session.patch(url, headers=headers, params=params, json=updates) as response:
            if response.status not in [200, 204]:
                raise Exception(f"Failed to update novel: {response.status}")

    async def update_rankings(self, session: aiohttp.ClientSession):
        """Update novel rankings"""
        try:
            # Clear existing rankings and fetch novels in parallel
            await self.clear_rankings(session)
            novels_data = await self.fetch_novels_for_ranking(session)
            
            rankings = []
            
            # Create overall rankings
            novels_sorted_overall = sorted(novels_data, key=lambda x: x.get('total_views', 0), reverse=True)
            for index, novel in enumerate(novels_sorted_overall):
                rankings.append({
                    'novel_id': novel['id'],
                    'type': 'overall',
                    'ranking': index + 1,
                    'metadata': {'total_views': novel.get('total_views', 0)}
                })
            
            # Create weekly rankings if enabled
            if ENABLE_WEEKLY_UPDATES:
                novels_sorted_weekly = sorted(novels_data, key=lambda x: x.get('page_views', 0), reverse=True)
                for index, novel in enumerate(novels_sorted_weekly):
                    rankings.append({
                        'novel_id': novel['id'],
                        'type': 'weekly',
                        'ranking': index + 1,
                        'metadata': {'weekly_views': novel.get('page_views', 0)}
                    })
            
            # Batch insert rankings
            if rankings:
                await self.insert_rankings(rankings, session)
            
            print(f"[RANKINGS] Updated {len(rankings)} ranking entries")
            
        except Exception as error:
            print(f"[RANKINGS] Error: {str(error)}")

    async def clear_rankings(self, session: aiohttp.ClientSession):
        """Clear existing rankings"""
        url = f"{self.supabase_url}rest/v1/popular"
        headers = {
            'Authorization': f'Bearer {self.supabase_anon_key}',
            'apikey': self.supabase_anon_key,
            'Content-Type': 'application/json'
        }
        params = {'id': 'neq.0'}
        
        async with session.delete(url, headers=headers, params=params) as response:
            if response.status not in [200, 204]:
                raise Exception(f"Failed to clear rankings: {response.status}")

    async def fetch_novels_for_ranking(self, session: aiohttp.ClientSession):
        """Fetch novels for ranking"""
        url = f"{self.supabase_url}rest/v1/novels"
        headers = {
            'Authorization': f'Bearer {self.supabase_anon_key}',
            'apikey': self.supabase_anon_key,
            'Content-Type': 'application/json'
        }
        params = {
            'select': 'id,total_views,page_views',
            'status': 'eq.published'
        }
        
        async with session.get(url, headers=headers, params=params) as response:
            if response.status != 200:
                raise Exception(f"Failed to fetch novels for ranking: {response.status}")
            return await response.json()

    async def insert_rankings(self, rankings: List[Dict], session: aiohttp.ClientSession):
        """Insert rankings into Supabase"""
        url = f"{self.supabase_url}rest/v1/popular"
        headers = {
            'Authorization': f'Bearer {self.supabase_anon_key}',
            'apikey': self.supabase_anon_key,
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal'
        }
        
        async with session.post(url, headers=headers, json=rankings) as response:
            if response.status not in [200, 201]:
                raise Exception(f"Failed to insert rankings: {response.status}")

    async def cleanup_orphaned_insights(self, session: aiohttp.ClientSession):
        """Cleanup orphaned insights"""
        try:
            # Fetch all insights from PostHog
            headers = {
                'Authorization': f'Bearer {self.posthog_api_key}',
                'Content-Type': 'application/json'
            }
            
            async with session.get(
                f'https://app.posthog.com/api/projects/{self.posthog_project_id}/insights/?limit=1000',
                headers=headers
            ) as response:
                if response.status != 200:
                    raise Exception(f"Failed to fetch insights: {response.status}")
                data = await response.json()
                all_insights = data.get('results', [])
            
            # Fetch novels with insight IDs
            novels_data = await self.fetch_novels(session)
            saved_insight_ids = set()
            
            for novel in novels_data:
                if novel.get('insight_id'):
                    saved_insight_ids.add(novel['insight_id'])
                if novel.get('insight_id_weekly'):
                    saved_insight_ids.add(novel['insight_id_weekly'])
            
            # Find orphaned insights
            orphaned_insights = [
                insight for insight in all_insights
                if insight.get('short_id') and insight['short_id'] not in saved_insight_ids
            ]
            
            # Delete orphaned insights with concurrency control
            delete_tasks = []
            for insight in orphaned_insights:
                delete_tasks.append({
                    'type': 'delete',
                    'task': self.delete_insight(insight['id'], session)
                })
            
            await self.execute_with_concurrency_limit(delete_tasks, MAX_CONCURRENT_REQUESTS)
            print(f"[CLEANUP] Processed {len(orphaned_insights)} orphaned insights")
            
        except Exception as error:
            print(f"[CLEANUP] Error: {str(error)}")

    async def delete_insight(self, insight_id: str, session: aiohttp.ClientSession):
        """Delete a single insight"""
        headers = {
            'Authorization': f'Bearer {self.posthog_api_key}',
            'Content-Type': 'application/json'
        }
        
        async with session.patch(
            f'https://app.posthog.com/api/projects/{self.posthog_project_id}/insights/{insight_id}/',
            headers=headers,
            json={'deleted': True}
        ) as response:
            return response.status in [200, 204]

# Main execution function
async def run_analytics_worker():
    """Run the analytics worker"""
    print("Optimized analytics worker starting...")
    print(f"- Weekly updates: {'ENABLED' if ENABLE_WEEKLY_UPDATES else 'DISABLED'}")
    print(f"- Max concurrent requests: {MAX_CONCURRENT_REQUESTS}")
    print(f"- Batch size: {BATCH_SIZE}")
    print(f"- Orphaned cleanup: {'ENABLED' if ENABLE_ORPHANED_INSIGHTS_CLEANUP else 'DISABLED'}")
    
    worker = AnalyticsWorker()
    result = await worker.run_analytics()
    print(f"Analytics worker completed: {result}")
    return result

if __name__ == "__main__":
    asyncio.run(run_analytics_worker()) 