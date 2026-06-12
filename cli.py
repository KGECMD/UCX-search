#!/usr/bin/env python3
"""
UCX Search - Enhanced CLI with all features
"""

import click
import os
import sys
from ucx_search_core import UCXSearch, YepScraper, TavilySearcher
import time

@click.group()
def cli():
    """🚀 UCX Search - Privacy-Focused Search Engine
    
    Primary: Yep (no API key needed)
    Fallback: Tavily API
    """
    pass

@cli.command()
@click.argument('query')
@click.option('--results', '-r', default=10, help='Number of results (1-50)', type=int)
@click.option('--parallel', '-p', is_flag=True, help='Search both sources in parallel')
@click.option('--save', '-s', is_flag=True, help='Save results to JSON')
@click.option('--tavily-key', envvar='TAVILY_API_KEY', required=True)
def search(query, results, parallel, save, tavily_key):
    """Search using UCX (Yep primary, Tavily fallback)"""
    
    click.secho(f"\n🚀 UCX Search: '{query}'", fg='cyan', bold=True)
    click.echo("─" * 60)
    
    ucx = UCXSearch(tavily_api_key=tavily_key)
    search_result = ucx.search(query, num_results=min(results, 50), parallel=parallel)
    
    if not search_result['success']:
        click.secho(f"❌ {search_result.get('error', 'Search failed')}", fg='red')
        return
    
    # Display results
    ucx.display_results(search_result)
    
    # Save options
    if save:
        file = ucx.save_results(search_result)
        click.secho(f"✅ Saved to: {file}", fg='green')

@cli.command()
@click.argument('query')
@click.option('--results', '-r', default=10, type=int, help='Number of results')
def yep_only(query, results):
    """Search Yep only (no fallback)"""
    
    click.secho(f"\n🌐 Yep Search: '{query}'", fg='cyan', bold=True)
    click.echo("─" * 60)
    
    scraper = YepScraper()
    yep_results = scraper.search(query, num_results=min(results, 50))
    
    if not yep_results:
        click.secho("❌ No results found on Yep", fg='red')
        return
    
    click.secho(f"✅ Found {len(yep_results)} results\n", fg='green')
    
    for i, result in enumerate(yep_results, 1):
        click.secho(f"{i}. {result['title'][:60]}", fg='cyan')
        click.echo(f"   🔗 {result['url']}")
        click.echo(f"   📝 {result['description'][:100]}...")
        click.echo()

@cli.command()
@click.argument('query')
@click.option('--results', '-r', default=10, type=int)
@click.option('--tavily-key', envvar='TAVILY_API_KEY', required=True)
def tavily_only(query, results, tavily_key):
    """Use Tavily API directly"""
    
    click.secho(f"\n🔄 Tavily Search: '{query}'", fg='cyan', bold=True)
    click.echo("─" * 60)
    
    searcher = TavilySearcher(tavily_key)
    tavily_results = searcher.search(query, num_results=min(results, 50))
    
    if not tavily_results:
        click.secho("❌ No results from Tavily", fg='red')
        return
    
    click.secho(f"✅ Found {len(tavily_results)} results\n", fg='green')
    
    for i, result in enumerate(tavily_results, 1):
        click.secho(f"{i}. {result['title'][:60]}", fg='cyan')
        click.echo(f"   🔗 {result['url']}")
        click.echo(f"   ⭐ Score: {result.get('score', 'N/A')}")
        click.echo()

@cli.command()
@click.option('--tavily-key', envvar='TAVILY_API_KEY', required=True)
def demo(tavily_key):
    """Run demo searches"""
    
    click.secho("\n" + "="*60, fg='cyan', bold=True)
    click.secho("🚀 UCX Search - Demo Mode", fg='cyan', bold=True)
    click.secho("="*60, fg='cyan')
    
    queries = [
        "Python web scraping",
        "AI latest news 2025",
        "privacy search engines"
    ]
    
    ucx = UCXSearch(tavily_api_key=tavily_key)
    
    for query in queries:
        click.secho(f"\n📌 Searching: '{query}'", fg='yellow')
        results = ucx.search(query, num_results=3)
        
        for i, result in enumerate(results['results'], 1):
            click.echo(f"\n{i}. {result['title'][:50]}")
            click.echo(f"   {result['url'][:50]}")
        
        time.sleep(1)
    
    click.secho("\n✅ Demo completed!", fg='green', bold=True)

@cli.command()
def version():
    """Show version info"""
    click.secho("UCX Search v2.0.0", fg='cyan', bold=True)
    click.echo("Privacy-First Search Engine")
    click.echo("Primary: Yep (no API key) • Fallback: Tavily")

if __name__ == '__main__':
    cli()
