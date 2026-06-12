#!/usr/bin/env python3
"""
UCX Search CLI - Enhanced with Chat and Multi-type Search
"""

import click
import os
from ucx_search_core import UCXSearch, YepScraper, TavilySearcher
import time

@click.group()
def cli():
    """🚀 UCX Search v2.5 - AI-Powered Privacy Search"""
    pass

@cli.command()
@click.argument('query')
@click.option('--type', '-t', 'search_type', default='web', type=click.Choice(['web', 'news', 'images']), help='Search type')
@click.option('--results', '-r', default=10, type=int, help='Number of results')
@click.option('--no-ai', is_flag=True, help='Disable AI features')
@click.option('--tavily-key', envvar='TAVILY_API_KEY', required=True)
def search(query, search_type, results, no_ai, tavily_key):
    """Search with UCX"""
    click.secho(f"\n🚀 UCX Search: '{query}'", fg='cyan', bold=True)
    
    ucx = UCXSearch(tavily_api_key=tavily_key)
    result = ucx.search(query, search_type=search_type, num_results=results, use_ai=not no_ai)
    
    if result['success']:
        click.secho(f"✅ Found {result['total']} results", fg='green')
        
        if result.get('ai_summary'):
            click.secho(f"\n🤖 Summary:\n{result['ai_summary']}", fg='blue')
        
        for i, r in enumerate(result['results'][:3], 1):
            click.echo(f"\n{i}. {r['title'][:60]}")
            click.echo(f"   {r['url'][:70]}")
    else:
        click.secho(f"❌ {result.get('error', 'Search failed')}", fg='red')

@cli.command()
@click.argument('message')
@click.option('--search', '-s', is_flag=True, help='Enable web search')
@click.option('--tavily-key', envvar='TAVILY_API_KEY', required=True)
def chat(message, search, tavily_key):
    """Chat with AI assistant"""
    click.secho(f"\n💬 You: {message}", fg='cyan')
    
    ucx = UCXSearch(tavily_api_key=tavily_key)
    response = ucx.chat(message, search_enabled=search)
    
    click.secho(f"\n🤖 Assistant:\n{response['response']}", fg='green')

@cli.command()
@click.argument('query')
@click.option('--results', '-r', default=10, type=int)
@click.option('--tavily-key', envvar='TAVILY_API_KEY', required=True)
def news(query, results, tavily_key):
    """Search news"""
    click.secho(f"\n📰 News Search: '{query}'", fg='yellow')
    
    ucx = UCXSearch(tavily_api_key=tavily_key)
    result = ucx.search(query, search_type='news', num_results=results)
    
    if result['success']:
        for i, r in enumerate(result['results'], 1):
            click.echo(f"\n{i}. {r['title'][:70]}")
            if r.get('date'):
                click.secho(f"   📅 {r['date']}", fg='blue')
            click.echo(f"   {r['url'][:70]}")
    else:
        click.secho("❌ No news found", fg='red')

if __name__ == '__main__':
    cli()
