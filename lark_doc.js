#!/usr/bin/env node
/**
 * 这是一个实现技术方案文档解析的 MCP (Model Context Protocol) 服务器模板。
 * 它通过以下功能演示了 MCP 的核心概念（资源、工具和提示）：
 * - 读取技术方案内容，并输出为prompt
 */
// 导入必要的 MCP SDK 组件
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
// 导入请求处理相关的模式定义
import { CallToolRequestSchema, // 列出资源请求模式
ListToolsRequestSchema, // 列出工具请求模式
 } from '@modelcontextprotocol/sdk/types.js';
// 飞书机器人应用的凭证
const appId = process.env.APP_ID || '';
const appSecret = process.env.APP_SECRET || '';
// 火山方舟API密钥
const arkApiKey = process.env.ARK_API_KEY || '';
const arkModel = process.env.ARK_MODEL || '';
/**
 * 创建 MCP 服务器实例
 * 配置服务器名称、版本，并启用资源、工具和提示功能
 */
const server = new Server({
    name: 'docx_mcp', // 服务器名称
    version: '0.1.0', // 服务器版本
}, {
    capabilities: {
        // 启用的功能
        resources: {}, // 资源功能
        tools: {}, // 工具功能
        prompts: {}, // 提示功能
    },
});
/**
 * 处理列出可用工具的请求
 * 暴露一个 "analysis_docx" 工具，允许用户解析飞书文档
 */
server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
        tools: [
            {
                name: 'analysis_docx',
                description: '解析飞书文档',
                inputSchema: {
                    type: 'object',
                    properties: {
                        documentUrl: {
                            type: 'string',
                            description: '飞书文档URL，例如：https://bytedance.larkoffice.com/docx/OS9YdoucMoHnISxlHzLcD3AIngg',
                        },
                    },
                    required: ['documentUrl'],
                },
            },
        ],
    };
});
/**
 * 从飞书文档URL中提取documentID
 * @param url 飞书文档URL
 * @returns documentID
 */
function extractDocumentIdFromUrl(url) {
    // 匹配格式：https://bytedance.larkoffice.com/docx/xxxxx 或者 https://bytedance.larkoffice.com/wiki/xxxxx
    const regex = /\/docx\/([A-Za-z0-9]+)|\/wiki\/([A-Za-z0-9]+)/;
    const match = url.match(regex);
    if (!match) {
        throw new Error('无效的飞书文档URL格式');
    }
    // 返回第一个或第二个捕获组的值(docx或wiki的ID)
    return match[1] || match[2];
}
/**
 * 使用火山方舟模型分析文档内容
 * @param docContent 文档内容
 * @returns 分析结果
 */
async function analyzeDocumentWithAI(docContent) {
    try {
        // 使用fetch直接调用火山方舟API
        const response = await fetch('https://ark-cn-beijing.bytedance.net/api/v3/chat/completions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${arkApiKey}`,
            },
            body: JSON.stringify({
                messages: [
                    { role: 'system', content: '你是一个专业的文档分析助手，请提炼文档中的关键信息并进行总结。' },
                    { role: 'user', content: docContent },
                ],
                model: arkModel, // 火山方舟模型ID
            }),
        });
        if (!response.ok) {
            throw new Error(`API请求失败: ${response.status} ${response.statusText}`);
        }
        const data = await response.json();
        return data.choices[0]?.message?.content || '无法分析文档内容';
    }
    catch (error) {
        console.error('调用AI模型失败:', error);
        return '调用AI模型分析文档时出错';
    }
}
// 判断文档链接是飞书云文档还是飞书知识库，云文档链接是docx/ 知识库链接是wiki/**
function isWikiUrl(url) {
    return url.includes('/wiki/');
}
/**
 * 处理工具调用请求
 */
server.setRequestHandler(CallToolRequestSchema, async (request) => {
    switch (request.params.name) {
        case 'analysis_docx': {
            const { documentUrl } = request.params.arguments;
            try {
                // 从URL中提取documentID
                let documentID = extractDocumentIdFromUrl(documentUrl);
                // 首先需要获取 access token
                const tokenResponse = await fetch('https://fsopen.bytedance.net/open-apis/auth/v3/tenant_access_token/internal/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        app_id: appId,
                        app_secret: appSecret,
                    }),
                });
                const tokenData = await tokenResponse.json();
                const token = tokenData.tenant_access_token;
                // 如果是知识库链接则需要先通过知识库ID获取云文档ID
                if (isWikiUrl(documentUrl)) {
                    const wikiResponse = await fetch(`https://open.larkoffice.com/open-apis/wiki/v2/spaces/get_node?token=${documentID}`, {
                        method: 'GET',
                        headers: {
                            Authorization: `Bearer ${token}`,
                        },
                    });
                    const wikiData = await wikiResponse.json();
                    documentID = wikiData.data.node.obj_token;
                }
                // 获取文档内容
                const docResponse = await fetch(`https://open.larkoffice.com/open-apis/docx/v1/documents/${documentID}/raw_content`, {
                    method: 'GET',
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                });
                const resData = await docResponse.json();
                const docContent = resData.data.content || 'test';
                // 使用AI分析文档内容
                const analysisResult = await analyzeDocumentWithAI(docContent);
                return {
                    content: [
                        {
                            type: 'text',
                            text: analysisResult,
                        },
                    ],
                };
            }
            catch (error) {
                console.error('处理文档失败:', error);
                return {
                    content: [
                        {
                            type: 'text',
                            text: `处理文档时出错: ${error.message || '未知错误'}`,
                        },
                    ],
                };
            }
        }
        default:
            throw new Error('未知工具');
    }
});
/**
 * 使用标准输入输出流启动服务器
 * 这允许服务器通过标准输入/输出流进行通信
 */
async function main() {
    const transport = new StdioServerTransport();
    await server.connect(transport);
}
// 错误处理
main().catch(error => {
    console.error('服务器错误:', error);
    process.exit(1);
});