class UserInterface:
    @staticmethod
    def get_search_results(results):
        """获取搜索结果并返回格式化字符串"""
        output = "\n搜索结果:\n"
        output += "=" * 80 + "\n"

        for idx, result in enumerate(results, 1):
            output += f"[{idx}] {result['title']}\n"
            output += (
                f" 作者: {result['author']} | 分类: {result['category']} | 页数: {result['pages']} | "
                f"评分: {result['rating']} | 时间: {result['timestamp']}\n"
            )
            output += f" 封面: {result['cover_url']}\n"
            output += f" 画廊链接: {result['gallery_url']}\n"
            output += "-" * 80 + "\n"
        return output

    @staticmethod
    def get_user_selection(max_idx):
        """获取用户选择"""
        while True:
            try:
                selection = int(input(f"\n请输入要下载的画廊编号 (1-{max_idx}): "))
                if 1 <= selection <= max_idx:
                    return selection
                print(f"请输入1-{max_idx}之间的数字")
            except ValueError:
                print("请输入有效的数字")

    @staticmethod
    def get_search_parameters():
        """获取搜索参数"""
        print("=" * 40)
        print("E-Hentai 爬虫")
        print("=" * 40)

        search_term = input("请输入搜索关键词: ").strip()
        min_rating = int(input("过滤最低评分（2-5，默认2）: ") or 2)
        min_pages = int(input("过滤最少页数（默认1）: ") or 1)
        target_page = int(input("获取第几页的画廊列表（默认1）: ") or 1)

        return {
            "search_term": search_term,
            "min_rating": min_rating,
            "min_pages": min_pages,
            "target_page": target_page
        }
