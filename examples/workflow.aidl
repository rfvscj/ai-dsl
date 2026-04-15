f summarize(items)
  = total len(items)
  ? total == 0
    r "empty"
  : 
    r f"items={total}"

= data ["tool", "memory", "plan"]
= tool_items F(data,len(_)>4)
= result summarize(data)
p result
p tool_items
