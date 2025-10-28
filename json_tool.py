#!/usr/bin/env python3
"""
JSON文件上传处理工具 - 命令行界面
用于演示和测试JSON文件处理功能
"""

import argparse
import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from json_file_handler import FileUploadProcessor


def main():
    parser = argparse.ArgumentParser(
        description="JSON文件上传处理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s config.json                    # 处理单个文件
  %(prog)s config.json -o output.json     # 指定输出文件
  %(prog)s config.json --summary          # 只显示摘要
  %(prog)s --cleanup 7                    # 清理7天前的旧文件
  %(prog)s --info                         # 显示支持的格式信息
        """
    )

    parser.add_argument(
        "file_path",
        nargs="?",
        help="要处理的JSON配置文件路径"
    )

    parser.add_argument(
        "-o", "--output",
        help="输出文件路径"
    )

    parser.add_argument(
        "--summary",
        action="store_true",
        help="只显示配置摘要"
    )

    parser.add_argument(
        "--cleanup",
        type=int,
        metavar="DAYS",
        help="清理指定天数前的旧文件"
    )

    parser.add_argument(
        "--info",
        action="store_true",
        help="显示支持的文件格式信息"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="详细输出"
    )

    args = parser.parse_args()

    # 创建处理器
    processor = FileUploadProcessor()

    if args.info:
        # 显示格式信息
        formats = processor.get_supported_formats()
        print("📋 支持的文件格式:")
        print(f"   扩展名: {', '.join(formats['extensions'])}")
        print(f"   最大大小: {formats['max_size']}")
        print(f"   编码: {formats['encoding']}")
        print("   必需结构:")
        for section, fields in formats['structure'].items():
            print(f"     {section}: {', '.join(fields)}")
        return

    if args.cleanup is not None:
        # 清理旧文件
        deleted_count = processor.cleanup_old_files(args.cleanup)
        print(f"🧹 已清理 {deleted_count} 个旧文件")
        return

    if not args.file_path:
        parser.error("必须指定文件路径，或使用 --info 或 --cleanup 选项")

    # 检查文件是否存在
    if not os.path.exists(args.file_path):
        print(f"❌ 文件不存在: {args.file_path}")
        sys.exit(1)

    # 处理文件
    print(f"⚙️ 正在处理文件: {args.file_path}")

    result = processor.process_uploaded_file(args.file_path)

    if result["success"]:
        print("✅ 文件处理成功")

        if args.summary:
            # 只显示摘要
            summary = result["summary"]
            print("\n📊 配置摘要:")
            print(f"   截面名称: {summary.get('section_name', 'N/A')}")
            print(f"   描述: {summary.get('description', 'N/A')}")
            print(f"   版本: {summary.get('version', 'N/A')}")
            print(f"   混凝土: {summary['materials']['concrete']}")
            print(f"   钢筋: {summary['materials']['steel']}")
            print(f"   截面高度: {summary['geometry']['height']} mm")
            print(f"   轮廓点数: {summary['geometry']['contour_points_count']}")
            print(f"   总钢筋面积: {summary['reinforcement']['total_steel_area']:.1f} mm²")
            print(f"   目标轴力: {summary['analysis']['target_axial_force']} kN")
        else:
            # 显示完整信息
            print(f"💾 处理后文件: {result['processed_file']}")

            if args.verbose:
                summary = result["summary"]
                print(f"\n🔍 详细摘要: {summary}")

    else:
        print(f"❌ 处理失败: {result['message']}")
        sys.exit(1)


if __name__ == "__main__":
    main()