from __future__ import annotations
def types_and_containers():
    i=42       #整数
    f=3.14     #浮点数
    b=True     #布尔值
    s="hello"   #字符串
    lst=[1,2,3]  #列表  有序可修改
    tpl=(4,5)    #元组 有序不可修改
    dct={"a":1,"b":2}  #字典-键值对，无序
    st ={1,1,2,3}    #集合 无序去重
    return i,f,b,s,lst,tpl,dct,st
def control_flow(n:int)->list[int]:# 类型注解表示函数接收整数参数返回整数列表
    out = []
    for x in range(n):#循环遍历从0到n-1
      if x%2 ==0:   #条件
        out.append(x)#向列表加入元素
    return out
def list_dict_comprehension(n:int):
   squares = [x*x for x in range(n) if x % 2 ==1]#列表推导式：生成 0 到 n-1 中奇数的平方
   mapping = {chr(97+i): i for i in range(n)}#字典推导式：生成键为 'a','b'...，值为 0,1... 的字典
   return squares, mapping
def file_io_demo(path:str):
   with open(path,"w",encoding="utf-8") as f:
      f.write("line1\nline2\nline3\n")
      with open (path,"r",encoding="utf-8") as f:
         data = f.read()
def exception_demo(x:str) ->int:
   try:
      return int(x)
   except ValueError as e:
      return -1 
def main():
    print("== types_and_containers ==")
    print(types_and_containers())
    print("== control_flow(10) ==")
    print(control_flow(10))
    print("== list_dict_comprehension(5) ==")
    print(list_dict_comprehension(5))
    print("== file_io_demo ==")
    print(file_io_demo("playground_tmp.txt"))
    print("== exception_demo('123') / ('oops') ==")
    print(exception_demo("123"), exception_demo("oops"))
if __name__ == "__main__":
   main()  
   
