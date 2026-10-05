export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const referer = request.headers.get('referer') || '';

    // 防盗链：/assets/ 全目录（含 html 卡片图/svg/png/css），外部 Referer 拦截
    const isAsset = url.pathname.startsWith('/assets/');
    if (isAsset && referer) {
      const refUrl = new URL(referer);
      const allowed = [
        'zhangxunnj.cc.cd',
        'zhangxunck.github.io',
        'google.com',
        'bing.com',
        'baidu.com'
      ];
      const isAllowed = allowed.some(d => refUrl.hostname === d || refUrl.hostname.endsWith('.' + d));
      if (!isAllowed) {
        return new Response('Hotlinking Forbidden by White Stone Spring', { status: 403 });
      }
    }

    // 路径重写：CF 自定义域名 -> GitHub Pages 子路径
    const targetUrl = new URL(
      url.pathname === '/' ? '/WhiteStoneXi/' : '/WhiteStoneXi' + url.pathname,
      'https://zhangxunck.github.io'
    );
    targetUrl.search = url.search;

    const modifiedRequest = new Request(targetUrl, {
      method: request.method,
      headers: request.headers,
      body: request.body,
      redirect: 'follow'
    });

    return await fetch(modifiedRequest);
  }
};
