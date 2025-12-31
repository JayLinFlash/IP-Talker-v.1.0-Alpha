import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import os
from datetime import datetime
import time
import re

class WebCrawler:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
    def is_valid_url(self, url):
        """验证URL是否有效"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def fetch_content(self, url, timeout=10):
        """获取网页内容"""
        try:
            response = requests.get(url, headers=self.headers, timeout=timeout)
            response.encoding = response.apparent_encoding  # 自动检测编码
            if response.status_code == 200:
                return response.text
            else:
                print(f"请求失败，状态码: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"请求错误: {e}")
            return None
    
    def extract_text(self, html_content):
        """提取网页文本内容"""
        if not html_content:
            return ""
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 移除不需要的元素
        for element in soup(['script', 'style', 'nav', 'footer', 'aside']):
            element.decompose()
        
        # 获取标题
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        else:
            # 尝试从h1标签获取标题
            h1 = soup.find('h1')
            if h1:
                title = h1.get_text().strip()
        
        # 获取正文内容
        # 方法1: 尝试找到主要内容区域
        main_content = ""
        main_tags = soup.find_all(['article', 'main', 'div'], class_=re.compile(r'(content|main|article|post)', re.I))
        
        if main_tags:
            for tag in main_tags:
                text = tag.get_text(separator='\n', strip=True)
                if len(text) > len(main_content):
                    main_content = text
        else:
            # 方法2: 提取所有段落
            paragraphs = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li'])
            main_content = '\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
        
        # 清理文本
        main_content = re.sub(r'\n\s*\n', '\n\n', main_content)  # 移除多余空行
        main_content = re.sub(r'[\t ]+', ' ', main_content)  # 移除多余空格
        
        return title, main_content
    
    def extract_links(self, html_content, base_url):
        """提取页面中的链接"""
        soup = BeautifulSoup(html_content, 'html.parser')
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            # 处理相对链接
            if href.startswith('/'):
                parsed_base = urlparse(base_url)
                href = f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
            elif href.startswith('http'):
                pass  # 已经是绝对链接
            else:
                continue  # 跳过其他类型的链接
            
            if self.is_valid_url(href):
                links.append({
                    'url': href,
                    'text': link.get_text(strip=True)[:100]  # 只取前100个字符
                })
        
        return links
    
    def extract_metadata(self, html_content):
        """提取元数据"""
        soup = BeautifulSoup(html_content, 'html.parser')
        metadata = {}
        
        # 提取meta标签
        meta_tags = soup.find_all('meta')
        for meta in meta_tags:
            name = meta.get('name') or meta.get('property')
            content = meta.get('content')
            if name and content:
                metadata[name] = content
        
        return metadata
    
    def save_to_file(self, url, title, content, links, metadata, output_dir='crawled_data'):
        """保存爬取结果到文件"""
        # 创建输出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 生成文件名（使用域名和当前时间戳）
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace('www.', '')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{domain}_{timestamp}"
        
        # 保存主内容
        main_file = os.path.join(output_dir, f"{filename}.txt")
        with open(main_file, 'w', encoding='utf-8') as f:
            f.write(f"URL: {url}\n")
            f.write(f"爬取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"标题: {title}\n\n")
            f.write("=" * 80 + "\n\n")
            f.write("正文内容:\n")
            f.write("=" * 80 + "\n\n")
            f.write(content)
            f.write("\n\n" + "=" * 80 + "\n")
            f.write(f"字符数: {len(content)}\n")
        
        # 保存链接信息
        links_file = os.path.join(output_dir, f"{filename}_links.txt")
        with open(links_file, 'w', encoding='utf-8') as f:
            f.write(f"URL: {url}\n")
            f.write(f"发现链接总数: {len(links)}\n\n")
            for i, link in enumerate(links, 1):
                f.write(f"{i}. {link['url']}\n")
                if link['text']:
                    f.write(f"   链接文本: {link['text']}\n")
                f.write("\n")
        
        # 保存元数据
        if metadata:
            meta_file = os.path.join(output_dir, f"{filename}_metadata.txt")
            with open(meta_file, 'w', encoding='utf-8') as f:
                f.write(f"URL: {url}\n")
                f.write("元数据:\n")
                f.write("=" * 80 + "\n")
                for key, value in metadata.items():
                    f.write(f"{key}: {value}\n")
        
        print(f"\n数据已保存到以下文件:")
        print(f"1. 主要内容: {main_file}")
        print(f"2. 链接列表: {links_file}")
        if metadata:
            print(f"3. 元数据: {meta_file}")
        
        return main_file
    
    def crawl(self, url, max_depth=1, current_depth=1, visited=None):
        """主爬取函数"""
        if visited is None:
            visited = set()
        
        if current_depth > max_depth or url in visited:
            return None
        
        visited.add(url)
        print(f"\n[{current_depth}/{max_depth}] 正在爬取: {url}")
        
        # 获取网页内容
        html_content = self.fetch_content(url)
        if not html_content:
            print(f"无法获取 {url} 的内容")
            return None
        
        # 提取信息
        title, content = self.extract_text(html_content)
        links = self.extract_links(html_content, url)
        metadata = self.extract_metadata(html_content)
        
        # 保存结果
        output_file = self.save_to_file(url, title, content, links, metadata)
        
        # 递归爬取链接（如果设置了深度>1）
        results = [{
            'url': url,
            'title': title,
            'content_length': len(content),
            'links_count': len(links),
            'output_file': output_file
        }]
        
        if current_depth < max_depth:
            for link in links[:5]:  # 限制每个页面只爬取前5个链接，避免过多请求
                time.sleep(1)  # 礼貌性延迟，避免对服务器造成压力
                result = self.crawl(link['url'], max_depth, current_depth + 1, visited)
                if result:
                    results.extend(result)
        
        return results

def main():
    print("=" * 60)
    print("网页爬虫工具 v1.0")
    print("=" * 60)
    
    crawler = WebCrawler()
    
    while True:
        url = input("\n请输入要爬取的URL (输入 'q' 退出): ").strip()
        
        if url.lower() == 'q':
            print("程序退出。")
            break
        
        if not crawler.is_valid_url(url):
            print("错误: 请输入有效的URL (例如: https://www.example.com)")
            continue
        
        try:
            depth = int(input("请输入爬取深度 (1-3，推荐1): ").strip() or "1")
            depth = max(1, min(3, depth))  # 限制在1-3之间
        except ValueError:
            depth = 1
            print("使用默认深度: 1")
        
        print(f"\n开始爬取 {url} (深度: {depth})")
        print("请稍候...")
        
        try:
            start_time = time.time()
            results = crawler.crawl(url, max_depth=depth)
            end_time = time.time()
            
            if results:
                total_pages = len(set(r['url'] for r in results))
                total_content = sum(r['content_length'] for r in results)
                
                print("\n" + "=" * 60)
                print("爬取完成!")
                print(f"总计爬取页面: {total_pages}")
                print(f"总计内容字符数: {total_content}")
                print(f"耗时: {end_time - start_time:.2f} 秒")
                print(f"数据保存在 'crawled_data' 文件夹中")
            else:
                print("爬取失败，请检查URL或网络连接。")
                
        except KeyboardInterrupt:
            print("\n\n用户中断爬取。")
        except Exception as e:
            print(f"发生错误: {e}")

if __name__ == "__main__":
    # 安装必要的库
    print("正在检查依赖...")
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        print("缺少必要的库，正在安装...")
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "beautifulsoup4"])
        print("安装完成，请重新运行程序。")
        exit(1)
    
    main()
