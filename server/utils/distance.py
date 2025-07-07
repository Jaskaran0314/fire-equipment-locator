"""
距离计算工具
使用Haversine公式计算两个经纬度点之间的距离
"""
import math

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    计算两个经纬度点之间的距离（米）
    使用Haversine公式
    
    Args:
        lat1: 第一个点的纬度
        lon1: 第一个点的经度
        lat2: 第二个点的纬度
        lon2: 第二个点的经度
        
    Returns:
        float: 两点之间的距离（米）
    """
    # 地球半径（米）
    R = 6371000
    
    # 将度转换为弧度
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    # Haversine公式
    a = math.sin(delta_lat / 2) ** 2 + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * \
        math.sin(delta_lon / 2) ** 2
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    # 计算距离
    distance = R * c
    
    return distance

def is_within_distance(lat1: float, lon1: float, lat2: float, lon2: float, 
                      max_distance: float) -> bool:
    """
    判断两个点是否在指定距离内
    
    Args:
        lat1: 第一个点的纬度
        lon1: 第一个点的经度
        lat2: 第二个点的纬度
        lon2: 第二个点的经度
        max_distance: 最大距离（米）
        
    Returns:
        bool: 是否在指定距离内
    """
    distance = calculate_distance(lat1, lon1, lat2, lon2)
    return distance <= max_distance