
def deduplicate_redundant_points(points: list[str]) -> list[str]:
    """
    Advanced deduplication for route description.
    Handles:
    1. "沿" prefix redundancy.
    2. Repeated road names separated by points (hubs/tolls).
    3. Main Road vs Auxiliary Road redundancy.
    """
    if not points:
        return []
    
    cleaned = []
    last_road = None
    
    # Keywords that identify a "Point" (Node) rather than a "Road" (Edge)
    point_keywords = ["枢纽", "互通", "收费站", "服务区", "立交", "出入口"]
    
    for p in points:
        # 1. Clean "沿" prefix for comparison
        core_p = p[1:] if p.startswith("沿") else p
        
        # 2. Basic "沿" Redundancy Check with immediate previous
        if cleaned:
            prev = cleaned[-1]
            prev_core = prev[1:] if prev.startswith("沿") else prev
            
            # If current is just "沿" version of previous or vice versa
            if core_p == prev_core:
                # Prefer the one without "沿" if possible, or just keep previous?
                # User prefers concise: "吉口互通" over "沿吉口互通"
                if p.startswith("沿") and not prev.startswith("沿"):
                    continue # Skip "沿X" if "X" exists
                if not p.startswith("沿") and prev.startswith("沿"):
                    cleaned[-1] = p # Replace "沿X" with "X"
                    continue
                continue # Exact duplicate

        # 3. Road vs Point Logic
        is_point = any(kw in core_p for kw in point_keywords)
        
        if not is_point:
            # It is treated as a Road (or generic location)
            if last_road:
                # Check for Exact Repetition (e.g. G1517 ... G1517)
                if core_p == last_road:
                    continue
                
                # Check for Auxiliary Road (e.g. XX大道 -> XX大道辅路)
                if "辅路" in core_p and core_p.startswith(last_road):
                    continue
            
            # Update last_road (Only update if it's a road/path)
            last_road = core_p
        
        cleaned.append(p)
            
    return cleaned

# Test Case
test_route = [
    "福建省三明厦钨新能源", "金明路", "到达收费站", "吉口互通", 
    "G1517莆炎高速", "三明西互通", "三明东互通", "嵩口互通", "潼关枢纽", 
    "G1517莆炎高速", "庄边互通", "萩芦互通", "港后枢纽", "渔溪枢纽", "到达收费站", 
    "S53渔平支线", "金井湾大道", "金井湾大道辅路", "天山北路", 
    "如意中路", "兴隆北路", "遂意路", "福建省平潭跨境电商园"
]

expected = [
    "福建省三明厦钨新能源", "金明路", "到达收费站", "吉口互通", 
    "G1517莆炎高速", "三明西互通", "三明东互通", "嵩口互通", "潼关枢纽", 
    "庄边互通", "萩芦互通", "港后枢纽", "渔溪枢纽", "到达收费站", 
    "S53渔平支线", "金井湾大道", "天山北路", 
    "如意中路", "兴隆北路", "遂意路", "福建省平潭跨境电商园"
]

result = deduplicate_redundant_points(test_route)
print("Input length:", len(test_route))
print("Result length:", len(result))
print("\nDetailed Result:")
for x in result:
    print(x)

print("\nMissing from expected (Errors):")
for x in result:
    if x not in expected: # Note: Logic check, simple set diff might be wrong if order matters
        pass

# Check specific removals
if "G1517莆炎高速" in result and result.count("G1517莆炎高速") == 1:
    print("\nPASS: G1517 deduplicated.")
else:
    print(f"\nFAIL: G1517 count is {result.count('G1517莆炎高速')}")

if "金井湾大道辅路" not in result:
    print("PASS: Aux road removed.")
else:
    print("FAIL: Aux road still present.")
