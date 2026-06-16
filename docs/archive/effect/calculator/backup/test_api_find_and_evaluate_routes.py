import requests
import json
import time

# API服务器地址
# BASE_URL = "http://103.40.13.100:10082"
BASE_URL = "http://localhost:8001"
def test_api_find_and_evaluate_routes():
    """
    测试/api_find_and_evaluate_routes接口
    """
    # 测试数据
    test_data = {
        "start_junction": "北村",
        "end_junction": "海沧",
        "loads_ton": [10, 15, 12],
        "spacings": [3.5, 1.2],
        "max_path_length": None,
        "top_n": 3
    }
    
    print("测试数据:")
    print(json.dumps(test_data, indent=2, ensure_ascii=False))
    print("\n" + "="*50 + "\n")
    
    # 记录开始时间
    start_time = time.time()
    
    # 发送POST请求
    try:
        response = requests.post(f"{BASE_URL}/api_find_and_evaluate_routes", json=test_data)
        
        # 记录结束时间
        end_time = time.time()
        response_time = end_time - start_time
        
        # 检查响应状态码
        if response.status_code == 200:
            print("请求成功！状态码:", response.status_code)
            print(f"API响应时间: {response_time:.3f} 秒")
            
            result = response.json()
            
            # 打印结果摘要
            print("\n结果摘要:")
            print(f"起点: {result.get('start_junction', 'N/A')}")
            print(f"终点: {result.get('end_junction', 'N/A')}")
            print(f"找到的路线数量: {result.get('route_count', 0)}")
            
            # 打印每条路线的详细信息
            route_evaluations = result.get('route_evaluations', [])
            for i, route in enumerate(route_evaluations, 1):
                print(f"\n路线 {i}:")
                print(f"  路径: {route.get('path_string', 'N/A')}")
                print(f"  是否可通行: {'是' if route.get('is_passable', False) else '否'}")
                print(f"  正弯矩效应比值范围: {route.get('pos_moment_ratio_range', 'N/A')}")
                print(f"  负弯矩效应比值范围: {route.get('neg_moment_ratio_range', 'N/A')}")
                print(f"  剪力效应比值范围: {route.get('shear_ratio_range', 'N/A')}")
                print(f"  最小效应比值: {route.get('min_effect_ratio', 'N/A')}")
                print(f"  桥梁总数: {route.get('total_bridge_count', 0)}")
                print(f"  路段数量: {route.get('section_count', 0)}")
                
                # 打印路径枢纽点经纬度信息
                path_locations = route.get('path_locations', [])
                if path_locations:
                    print("  路径枢纽点经纬度信息:")
                    for loc in path_locations:
                        print(f"    {loc.get('junction', 'N/A')}: {loc.get('location', 'N/A')}")
            
            # 保存完整结果到JSON文件
            with open('api_find_and_evaluate_routes_test_result.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print("\n完整结果已保存到 api_find_and_evaluate_routes_test_result.json")
            
            return result, response_time  # 返回结果和响应时间
        else:
            print(f"请求失败！状态码: {response.status_code}")
            print("错误信息:", response.text)
            return None, None
            
    except requests.exceptions.RequestException as e:
        print(f"请求过程中发生错误: {str(e)}")
        return None, None

if __name__ == "__main__":
    print("开始测试 /api_find_and_evaluate_routes 接口...")
    result, response_time = test_api_find_and_evaluate_routes()
    
    if result:
        print(f"\n测试完成！总耗时: {response_time:.3f} 秒")
    else:
        print("\n测试失败！")