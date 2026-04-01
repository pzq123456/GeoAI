import os
import sqlite3
import asyncio
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.deepseek import DeepSeekProvider

import logfire

# 1. 配置 logfire 输出到控制台
# 如果你不想注册账号，直接设为 'console' 即可在终端看到炫酷的彩色日志
logfire.configure(send_to_logfire='never') 

# 2. 告诉 Pydantic AI 监控这个 Agent
# 在你定义 model 之后，agent 之前加上这句：
logfire.instrument_pydantic_ai()

load_dotenv()

# --- 1. 数据结构与数据库 ---
@dataclass
class DatabaseConn:
    sqlite_conn: sqlite3.Connection

    async def get_customer(self, id: int):
        cur = self.sqlite_conn.cursor()
        res = cur.execute('SELECT name, balance FROM customers WHERE id=?', (id,))
        return res.fetchone()

    async def get_transactions(self, id: int) -> List[str]:
        cur = self.sqlite_conn.cursor()
        res = cur.execute('SELECT description, amount FROM transactions WHERE customer_id=?', (id,))
        return [f"目标: {row[0]}, 金额: {row[1]}" for row in res.fetchall()]

    async def update_balance(self, id: int, amount: float, description: str):
        cur = self.sqlite_conn.cursor()
        # 简单事务处理
        cur.execute('UPDATE customers SET balance = balance + ? WHERE id = ?', (amount, id))
        cur.execute('INSERT INTO transactions VALUES (?, ?, ?)', (id, description, abs(amount)))
        self.sqlite_conn.commit()

@dataclass
class SupportDependencies:
    customer_id: int
    db: DatabaseConn

# 结构化输出：现在包含一个“处理步骤”列表，展示规划过程
class SupportOutput(BaseModel):
    plan_steps: List[str] = Field(description="Agent 执行任务的思考与规划步骤")
    final_response: str = Field(description="最终给客户的回复")
    action_taken: bool = Field(description="是否实际执行了资金划拨或关键修改")

# --- 2. 定义 Agent ---
model = OpenAIChatModel(
    model_name='deepseek-chat',
    provider=DeepSeekProvider(api_key=os.getenv('DEEPSEEK_API_KEY')),
)

support_agent = Agent(
    model=model,
    deps_type=SupportDependencies,
    output_type=SupportOutput,
    instructions=(
        '你是一个拥有高级权限的银行数字助理。'
        '对于复杂的请求，你必须：1. 分析需求 2. 检查前置条件（如余额是否足够）3. 执行操作 4. 汇总结果。'
        '回复必须亲切，且始终提及客户姓名。'
    ),
)

# --- 3. 注册工具 ---
@support_agent.tool
async def check_balance_and_name(ctx: RunContext[SupportDependencies]) -> dict:
    """查询当前客户的姓名和余额明细。"""
    row = await ctx.deps.db.get_customer(ctx.deps.customer_id)
    return {"name": row[0], "balance": row[1]}

@support_agent.tool
async def list_recent_transactions(ctx: RunContext[SupportDependencies]) -> List[str]:
    """获取最近的所有转账流水记录。"""
    return await ctx.deps.db.get_transactions(ctx.deps.customer_id)

@support_agent.tool
async def execute_transfer(ctx: RunContext[SupportDependencies], amount: float, recipient: str) -> str:
    """
    执行转账操作。
    注意：调用前必须先确认余额是否足够。
    """
    customer = await ctx.deps.db.get_customer(ctx.deps.customer_id)
    current_balance = customer[1]
    if current_balance < amount:
        return f"转账失败：当前余额 {current_balance} 不足支出 {amount}"
    
    await ctx.deps.db.update_balance(ctx.deps.customer_id, -amount, f"转账给 {recipient}")
    return f"成功向 {recipient} 转账 {amount} 元。"

# --- 4. 运行演示 ---
async def main():
    # 初始化一个真实的模拟数据库
    with sqlite3.connect(':memory:') as con:
        cur = con.cursor()
        cur.execute('CREATE TABLE customers(id INTEGER, name TEXT, balance REAL)')
        cur.execute('CREATE TABLE transactions(customer_id INTEGER, description TEXT, amount REAL)')
        cur.execute("INSERT INTO customers VALUES (123, '张三', 200.00)")
        cur.execute("INSERT INTO transactions VALUES (123, '给李四转账', 50.00)")
        con.commit()

        deps = SupportDependencies(customer_id=123, db=DatabaseConn(sqlite_conn=con))

        # 复杂长任务需求
        complex_query = "帮我查查最近是不是给李四转过钱？如果转过，且我现在余额还够 100 块的话，就再给他转 60 元。"
        
        print(f"🚀 用户请求: {complex_query}\n")
        
        result = await support_agent.run(complex_query, deps=deps)
        
        print("--- Agent 规划步骤 ---")
        for i, step in enumerate(result.output.plan_steps, 1):
            print(f"{i}. {step}")
            
        print(f"\n💬 最终回复: {result.output.final_response}")
        print(f"🛠️ 实际操作执行: {'是' if result.output.action_taken else '否'}")

        # 验证数据库是否真的变动了
        new_balance = (await deps.db.get_customer(123))[1]
        print(f"\n💰 数据库最新余额: {new_balance} 元")

if __name__ == '__main__':
    asyncio.run(main())