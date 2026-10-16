"""Public page reader using a separate browser, with bounded GET-only proxying."""
import os,time
from pathlib import Path
from .public_http import fetch,endpoint,ConnectorError


def read_page(url,home):
    try:from playwright.sync_api import sync_playwright
    except ImportError:raise ConnectorError('PLAYWRIGHT_MISSING : exécuter scripts/INSTALLER_RECHERCHE.cmd') from None
    os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH',str(Path(home).parent/'browsers'))
    origin=endpoint(url).netloc
    with sync_playwright() as p:
        try:browser=p.chromium.launch(headless=True,args=['--disable-background-networking','--disable-quic','--disable-webrtc'])
        except Exception:raise ConnectorError('CHROMIUM_MISSING : exécuter scripts/INSTALLER_RECHERCHE.cmd') from None
        try:
            context=browser.new_context(service_workers='block',accept_downloads=False)
            context.route_web_socket('**/*',lambda ws:ws.close())
            count=0;started=time.monotonic();total=0;failed=[]
            def handle(route):
                nonlocal count,total
                req=route.request
                try:
                    if req.method!='GET' or req.resource_type not in ('document','script','stylesheet','xhr','fetch'):
                        return route.abort()
                    if endpoint(req.url).netloc!=origin or count>=20 or time.monotonic()-started>40:return route.abort()
                    count+=1
                    body,headers=fetch(req.url,max_bytes=500_000)
                    total+=len(body)
                    if total>3_000_000:return route.abort()
                    return route.fulfill(status=200,body=body,headers={'content-type':headers.get('content-type','text/plain')})
                except Exception:
                    if req.is_navigation_request():failed.append(True)
                    route.abort()
            context.route('**/*',handle)
            page=context.new_page()
            try:
                page.goto(url,wait_until='domcontentloaded',timeout=45000)
                text=page.locator('body').inner_text(timeout=5000)
                if failed or len(text.strip())<40:raise ConnectorError('Page non exploitable')
                return text[:24000]
            except ConnectorError:raise
            except Exception:raise ConnectorError('Page dynamique indisponible, redirection ou ressources non autorisées') from None
        finally:browser.close()
