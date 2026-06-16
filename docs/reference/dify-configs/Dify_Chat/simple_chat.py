import requests
import json


# 用于运输申请对话;

def send_dify_request(query, api_key="app-UnUkfuh00Z4WrEYKlvvmVZs2", conversation_id="", user="user-123"):
    """
    发送Dify API请求
    
    参数:
    - query: 要发送的问题
    - api_key: API密钥
    - conversation_id: 对话ID，用于保持对话上下文
    - user: 用户ID
    
    返回:
    - API响应数据
    """
    url = "http://103.40.13.100:23452/v1/chat-messages"
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    data = {
        "inputs": {},
        "query": query,
        "response_mode": "blocking",
        "conversation_id": conversation_id,
        "user": user,
        "files": []
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        print(f"请求出错: {e}")
        return None

def main():
    """主函数 - 简单交互式对话"""
    print("Dify API 简单对话工具")
    print("=" * 50)
    print("输入 'quit' 退出对话")
    print("输入 'test' 运行预设测试问题")
    print("=" * 50)
    
    conversation_id = ""
    
    # 首先自动运行预设测试问题
    print("\n正在自动运行预设测试问题...")
    test_question = "我现在需要填写运输申请表，如何确定自己的运输车辆型号？有没有示意图？"
    print(f"测试问题: {test_question}")
    
    print("\n正在发送请求...")
    response = send_dify_request(test_question, conversation_id=conversation_id)
    
    if response:
        if "answer" in response:
            print(f"\n回答: {response['answer']}")
            
            # 更新对话ID
            if "conversation_id" in response:
                conversation_id = response["conversation_id"]
                print(f"对话ID: {conversation_id}")
        else:
            print("\n完整响应:")
            print(json.dumps(response, indent=2, ensure_ascii=False))
    else:
        print("\n请求失败，请检查网络连接和API配置。")
    
    # 然后进入交互式对话
    while True:
        try:
            user_input = input("\n请输入问题: ")
            
            if user_input.lower() == 'quit':
                print("感谢使用，再见！")
                break
            elif user_input.lower() == 'test':
                print(f"\n测试问题: {test_question}")
                print("\n正在发送请求...")
                response = send_dify_request(test_question, conversation_id=conversation_id)
                
                if response:
                    if "answer" in response:
                        print(f"\n回答: {response['answer']}")
                        
                        # 更新对话ID
                        if "conversation_id" in response:
                            conversation_id = response["conversation_id"]
                            print(f"对话ID: {conversation_id}")
                    else:
                        print("\n完整响应:")
                        print(json.dumps(response, indent=2, ensure_ascii=False))
                else:
                    print("\n请求失败，请检查网络连接和API配置。")
            elif not user_input.strip():
                continue
            
            print("\n正在发送请求...")
            response = send_dify_request(user_input, conversation_id=conversation_id)
            
            if response:
                if "answer" in response:
                    print(f"\n回答: {response['answer']}")
                    
                    # 更新对话ID
                    if "conversation_id" in response:
                        conversation_id = response["conversation_id"]
                        print(f"对话ID: {conversation_id}")
                else:
                    print("\n完整响应:")
                    print(json.dumps(response, indent=2, ensure_ascii=False))
            else:
                print("\n请求失败，请检查网络连接和API配置。")
        
        except KeyboardInterrupt:
            print("\n\n程序被用户中断，退出。")
            break
        except EOFError:
            print("\n\n检测到EOF，退出程序。")
            break

if __name__ == "__main__":
    main()