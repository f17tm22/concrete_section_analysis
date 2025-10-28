#!/usr/bin/env python3
"""
JSON文件上传和处理接口
用于处理不规则截面分析的JSON配置文件上传、验证和预处理
"""

import json
import os
import sys
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from analyzer_ver1 import RCSectionAnalyzer


class JSONFileHandler:
    """JSON文件处理类"""

    def __init__(self):
        """初始化文件处理器"""
        self.analyzer = RCSectionAnalyzer()
        self.supported_concrete_types = set(self.analyzer.CONCRETE_TYPES.keys())
        self.supported_steel_types = set(self.analyzer.STEEL_TYPES.keys())

    def validate_json_structure(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        验证JSON文件结构

        Args:
            data: 解析后的JSON数据

        Returns:
            (is_valid, error_message): 验证结果和错误信息
        """
        try:
            # 检查必需的顶级字段
            required_fields = ["materials", "geometry", "reinforcement", "analysis"]
            for field in required_fields:
                if field not in data:
                    return False, f"缺少必需字段: {field}"

            # 验证材料信息
            materials = data["materials"]
            if "concrete_type" not in materials or "steel_type" not in materials:
                return False, "材料信息不完整"

            if materials["concrete_type"] not in self.supported_concrete_types:
                return False, f"不支持的混凝土类型: {materials['concrete_type']}"

            if materials["steel_type"] not in self.supported_steel_types:
                return False, f"不支持的钢筋类型: {materials['steel_type']}"

            # 验证几何信息
            geometry = data["geometry"]
            if "height" not in geometry or "contour_points" not in geometry:
                return False, "几何信息不完整"

            if not isinstance(geometry["contour_points"], list) or len(geometry["contour_points"]) < 2:
                return False, "轮廓点数据无效"

            # 验证每个轮廓点
            for i, point in enumerate(geometry["contour_points"]):
                if "y" not in point or "half_width" not in point:
                    return False, f"轮廓点 {i} 数据不完整"

            # 验证钢筋配置
            reinforcement = data["reinforcement"]
            if "cover_thickness" not in reinforcement or "layers" not in reinforcement:
                return False, "钢筋配置信息不完整"

            required_layers = ["top", "middle", "bottom"]
            for layer_name in required_layers:
                if layer_name not in reinforcement["layers"]:
                    return False, f"缺少钢筋层: {layer_name}"

                layer = reinforcement["layers"][layer_name]
                required_layer_fields = ["count", "diameter"]
                for field in required_layer_fields:
                    if field not in layer:
                        return False, f"钢筋层 {layer_name} 缺少字段: {field}"

            # 验证分析参数
            analysis = data["analysis"]
            if "target_axial_force" not in analysis or "curvature_range" not in analysis:
                return False, "分析参数不完整"

            curvature_range = analysis["curvature_range"]
            required_range_fields = ["start", "end", "steps"]
            for field in required_range_fields:
                if field not in curvature_range:
                    return False, f"曲率范围缺少字段: {field}"

            return True, "JSON文件结构验证通过"

        except Exception as e:
            return False, f"JSON结构验证失败: {str(e)}"

    def load_json_file(self, file_path: str) -> Tuple[bool, Dict[str, Any], str]:
        """
        加载和验证JSON文件

        Args:
            file_path: JSON文件路径

        Returns:
            (success, data, message): 加载结果、数据和消息
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                return False, {}, f"文件不存在: {file_path}"

            # 检查文件扩展名
            if not file_path.lower().endswith('.json'):
                return False, {}, f"文件格式错误，应为JSON文件: {file_path}"

            # 检查文件大小（限制为10MB）
            file_size = os.path.getsize(file_path)
            if file_size > 10 * 1024 * 1024:
                return False, {}, f"文件过大: {file_size} bytes (最大10MB)"

            # 读取和解析JSON
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 验证JSON结构
            is_valid, error_msg = self.validate_json_structure(data)
            if not is_valid:
                return False, {}, f"JSON文件验证失败: {error_msg}"

            logger.info(f"成功加载JSON文件: {file_path}")
            return True, data, "文件加载成功"

        except json.JSONDecodeError as e:
            return False, {}, f"JSON解析错误: {str(e)}"
        except PermissionError:
            return False, {}, f"文件权限错误，无法读取: {file_path}"
        except Exception as e:
            return False, {}, f"文件加载失败: {str(e)}"

    def preprocess_config_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        预处理配置文件数据，添加计算字段和验证

        Args:
            data: 原始配置数据

        Returns:
            处理后的配置数据
        """
        try:
            processed_data = data.copy()

            # 设置材料参数并获取计算值
            self.analyzer.set_materials(
                data["materials"]["concrete_type"],
                data["materials"]["steel_type"]
            )

            # 添加材料计算参数
            processed_data["materials"]["calculated_params"] = {
                "f_cd": self.analyzer.f_cd,
                "f_td": self.analyzer.f_td,
                "E_c": self.analyzer.E_c,
                "epsu": self.analyzer.epsu,
                "f_yd": self.analyzer.f_yd,
                "E_s": self.analyzer.E_s
            }

            # 计算钢筋面积
            reinforcement = processed_data["reinforcement"]
            steel_areas = {}

            for layer_name, layer_info in reinforcement["layers"].items():
                count = layer_info["count"]
                diameter = layer_info["diameter"]
                area = count * 3.14159265359 * (diameter / 2) ** 2
                steel_areas[layer_name] = area

            # 添加计算的钢筋面积
            reinforcement["calculated_areas"] = steel_areas

            # 验证几何合理性
            geometry = processed_data["geometry"]
            height = geometry["height"]
            contour_points = geometry["contour_points"]

            # 检查轮廓点Y坐标范围
            y_coords = [point["y"] for point in contour_points]
            if min(y_coords) != 0 or max(y_coords) != height:
                logger.warning("轮廓点Y坐标范围可能不正确")

            # 检查半宽度合理性
            half_widths = [point["half_width"] for point in contour_points]
            if any(w <= 0 for w in half_widths):
                logger.warning("发现非正的半宽度值")

            logger.info("配置文件预处理完成")
            return processed_data

        except Exception as e:
            logger.error(f"配置文件预处理失败: {str(e)}")
            raise

    def save_processed_config(self, data: Dict[str, Any], output_path: str) -> bool:
        """
        保存处理后的配置文件

        Args:
            data: 处理后的配置数据
            output_path: 输出文件路径

        Returns:
            保存是否成功
        """
        try:
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # 保存文件
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"处理后的配置文件已保存: {output_path}")
            return True

        except Exception as e:
            logger.error(f"保存配置文件失败: {str(e)}")
            return False

    def get_config_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取配置文件的摘要信息

        Args:
            data: 配置数据

        Returns:
            摘要信息字典
        """
        try:
            materials = data["materials"]
            geometry = data["geometry"]
            reinforcement = data["reinforcement"]
            analysis = data["analysis"]

            # 计算总钢筋面积
            total_steel_area = sum(reinforcement.get("calculated_areas", {}).values())

            summary = {
                "section_name": data.get("section_name", "未命名截面"),
                "description": data.get("description", ""),
                "version": data.get("version", "1.0"),
                "materials": {
                    "concrete": materials["concrete_type"],
                    "steel": materials["steel_type"]
                },
                "geometry": {
                    "height": geometry["height"],
                    "contour_points_count": len(geometry["contour_points"])
                },
                "reinforcement": {
                    "cover_thickness": reinforcement["cover_thickness"],
                    "total_steel_area": total_steel_area,
                    "layers": list(reinforcement["layers"].keys())
                },
                "analysis": {
                    "target_axial_force": analysis["target_axial_force"],
                    "curvature_range": analysis["curvature_range"]
                }
            }

            return summary

        except Exception as e:
            logger.error(f"生成配置摘要失败: {str(e)}")
            return {}


class FileUploadProcessor:
    """文件上传处理器"""

    def __init__(self, upload_dir: str = "uploads", processed_dir: str = "processed"):
        """
        初始化文件上传处理器

        Args:
            upload_dir: 上传文件目录
            processed_dir: 处理后文件目录
        """
        self.upload_dir = Path(upload_dir)
        self.processed_dir = Path(processed_dir)
        self.handler = JSONFileHandler()

        # 创建目录
        self.upload_dir.mkdir(exist_ok=True)
        self.processed_dir.mkdir(exist_ok=True)

    def process_uploaded_file(self, file_path: str) -> Dict[str, Any]:
        """
        处理上传的文件

        Args:
            file_path: 上传的文件路径

        Returns:
            处理结果字典
        """
        result = {
            "success": False,
            "message": "",
            "data": {},
            "summary": {},
            "processed_file": ""
        }

        try:
            # 加载和验证文件
            success, data, message = self.handler.load_json_file(file_path)
            if not success:
                result["message"] = message
                return result

            # 预处理数据
            processed_data = self.handler.preprocess_config_data(data)

            # 生成摘要
            summary = self.handler.get_config_summary(processed_data)

            # 保存处理后的文件
            filename = Path(file_path).stem
            processed_file = self.processed_dir / f"{filename}_processed.json"

            if self.handler.save_processed_config(processed_data, str(processed_file)):
                result["success"] = True
                result["message"] = "文件处理成功"
                result["data"] = processed_data
                result["summary"] = summary
                result["processed_file"] = str(processed_file)
            else:
                result["message"] = "保存处理后文件失败"

        except Exception as e:
            result["message"] = f"文件处理失败: {str(e)}"
            logger.error(f"处理上传文件失败: {str(e)}")

        return result

    def get_supported_formats(self) -> Dict[str, Any]:
        """获取支持的文件格式信息"""
        return {
            "extensions": [".json"],
            "max_size": "10MB",
            "encoding": "UTF-8",
            "structure": {
                "materials": ["concrete_type", "steel_type"],
                "geometry": ["height", "contour_points"],
                "reinforcement": ["cover_thickness", "layers"],
                "analysis": ["target_axial_force", "curvature_range"]
            }
        }

    def cleanup_old_files(self, days: int = 7) -> int:
        """
        清理旧文件

        Args:
            days: 保留天数

        Returns:
            删除的文件数量
        """
        import time
        current_time = time.time()
        cutoff_time = current_time - (days * 24 * 60 * 60)

        deleted_count = 0

        # 清理上传目录
        for file_path in self.upload_dir.glob("*"):
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                file_path.unlink()
                deleted_count += 1

        # 清理处理目录
        for file_path in self.processed_dir.glob("*"):
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                file_path.unlink()
                deleted_count += 1

        logger.info(f"清理了 {deleted_count} 个旧文件")
        return deleted_count


def main():
    """主函数，用于命令行测试"""
    import argparse

    parser = argparse.ArgumentParser(description="JSON文件上传处理器")
    parser.add_argument("file_path", help="要处理的JSON文件路径")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 创建处理器
    processor = FileUploadProcessor()

    # 处理文件
    result = processor.process_uploaded_file(args.file_path)

    if result["success"]:
        print("✅ 文件处理成功")
        print(f"📄 摘要信息: {result['summary']}")

        if args.output:
            # 如果指定了输出路径，复制处理后的文件
            import shutil
            shutil.copy2(result["processed_file"], args.output)
            print(f"💾 处理后文件已保存到: {args.output}")
        else:
            print(f"💾 处理后文件位置: {result['processed_file']}")
    else:
        print(f"❌ 文件处理失败: {result['message']}")
        sys.exit(1)


if __name__ == "__main__":
    main()