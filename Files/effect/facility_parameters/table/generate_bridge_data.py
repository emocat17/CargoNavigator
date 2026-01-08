import os
import shutil
import pandas as pd
import re

def read_bridge_list_excel(excel_path):
    """读取桥梁列表Excel文件，获取桩号数据"""
    try:
        # 读取Excel文件
        df = pd.read_excel(excel_path)
        # 假设桩号数据在第一列
        pile_numbers = df.iloc[:, 0].tolist()
        # 过滤掉空值和已存在的桩号（K0+3, K0+9, K0+15）
        existing_piles = ['K0+3', 'K0+9', 'K0+15']
        pile_numbers = [str(pile).strip() for pile in pile_numbers if pd.notna(pile) and str(pile).strip() not in existing_piles]
        return pile_numbers
    except Exception as e:
        print(f"读取Excel文件出错: {e}")
        return []

def copy_and_rename_folders(base_path, template_folders, pile_numbers):
    """复制模板文件夹并根据桩号重命名"""
    for pile_number in pile_numbers:
        print(f"正在处理桩号: {pile_number}")
        
        # 随机选择一个模板文件夹（K0+9或K0+15）
        template_folder = template_folders[0] if hash(pile_number) % 2 == 0 else template_folders[1]
        template_path = os.path.join(base_path, template_folder)
        
        # 创建新文件夹路径
        new_folder_path = os.path.join(base_path, pile_number)
        
        # 如果文件夹已存在，跳过
        if os.path.exists(new_folder_path):
            print(f"文件夹 {pile_number} 已存在，跳过")
            continue
            
        try:
            # 复制模板文件夹到新位置
            shutil.copytree(template_path, new_folder_path)
            print(f"已复制 {template_folder} 到 {pile_number}")
            
            # 重命名文件夹中的文件
            rename_files_in_folder(new_folder_path, template_folder, pile_number)
            
        except Exception as e:
            print(f"处理桩号 {pile_number} 时出错: {e}")

def rename_files_in_folder(folder_path, old_pile, new_pile):
    """重命名文件夹中的文件并替换文件内容"""
    for filename in os.listdir(folder_path):
        old_file_path = os.path.join(folder_path, filename)
        
        # 只处理.txt文件
        if not filename.endswith('.txt'):
            continue
            
        # 构建新文件名
        new_filename = filename.replace(old_pile, new_pile)
        new_file_path = os.path.join(folder_path, new_filename)
        
        try:
            # 重命名文件
            os.rename(old_file_path, new_file_path)
            
            # 读取文件内容并替换桩号
            with open(new_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 替换文件内容中的桩号
            # 对于K0+9，替换"K0+9连续T梁3x40m"为新桩号+"连续T梁3x40m"
            # 对于K0+15，替换"K0+15九龙江大桥"为新桩号+"九龙江大桥"
            if old_pile == "K0+9":
                old_pattern = f"{old_pile}连续T梁3x40m"
                new_pattern = f"{new_pile}连续T梁3x40m"
            elif old_pile == "K0+15":
                old_pattern = f"{old_pile}九龙江大桥"
                new_pattern = f"{new_pile}九龙江大桥"
            else:
                old_pattern = old_pile
                new_pattern = new_pile
                
            content = content.replace(old_pattern, new_pattern)
            
            # 写入新内容
            with open(new_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            print(f"已重命名并更新文件内容: {filename} -> {new_filename}")
            
        except Exception as e:
            print(f"处理文件 {filename} 时出错: {e}")

def main():
    # 基础路径
    base_path = r"D:/SourceTree/front/Files/effect/facility_parameters/bridge"
    
    # Excel文件路径
    excel_path = os.path.join(base_path, "bridge_list.xlsx")
    
    # 模板文件夹
    template_folders = ["K0+9", "K0+15"]
    
    # 读取桩号数据
    pile_numbers = read_bridge_list_excel(excel_path)
    
    if not pile_numbers:
        print("未找到有效的桩号数据")
        return
    
    print(f"找到 {len(pile_numbers)} 个桩号需要处理")
    
    # 复制并重命名文件夹
    copy_and_rename_folders(base_path, template_folders, pile_numbers)
    
    print("处理完成")

if __name__ == "__main__":
    main()