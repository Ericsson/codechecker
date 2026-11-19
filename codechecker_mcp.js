#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { Server } = require('@modelcontextprotocol/sdk/server/index.js');
const { StdioServerTransport } = require('@modelcontextprotocol/sdk/server/stdio.js');
const {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError,
} = require('@modelcontextprotocol/sdk/types.js');

// Configure paths
const DOCS_PATH = path.join(__dirname, 'docs');

class CodeCheckerMCPServer {
  constructor() {
    this.server = new Server(
      {
        name: 'codechecker-docs',
        version: '0.1.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );
    
    this.setupToolHandlers();
    this.documentIndex = null;
    this.initializeIndex();
  }

  async initializeIndex() {
    console.error('Indexing CodeChecker documentation...');
    this.documentIndex = await this.buildDocumentIndex();
    console.error(`Indexed ${Object.keys(this.documentIndex).length} documents`);
  }

  async buildDocumentIndex() {
    const index = {};
    
    const indexDirectory = (dirPath, relativePath = '') => {
      const items = fs.readdirSync(dirPath);
      
      for (const item of items) {
        const fullPath = path.join(dirPath, item);
        const relativeFilePath = path.join(relativePath, item);
        
        if (fs.statSync(fullPath).isDirectory()) {
          indexDirectory(fullPath, relativeFilePath);
        } else if (item.endsWith('.md')) {
          try {
            const content = fs.readFileSync(fullPath, 'utf8');
            const title = this.extractTitle(content, item);
            
            index[relativeFilePath] = {
              title,
              content,
              path: relativeFilePath,
              size: content.length,
              sections: this.extractSections(content)
            };
          } catch (error) {
            console.error(`Error reading ${fullPath}:`, error.message);
          }
        }
      }
    };
    
    indexDirectory(DOCS_PATH);
    return index;
  }

  extractTitle(content, filename) {
    // Try to find markdown title
    const titleMatch = content.match(/^#\s+(.+)$/m);
    if (titleMatch) {
      return titleMatch[1].trim();
    }
    
    // Fallback to filename
    return filename.replace('.md', '').replace(/[_-]/g, ' ');
  }

  extractSections(content) {
    const sections = [];
    const lines = content.split('\n');
    let currentSection = null;
    let currentContent = [];
    
    for (const line of lines) {
      const headerMatch = line.match(/^(#{1,6})\s+(.+)$/);
      
      if (headerMatch) {
        // Save previous section
        if (currentSection) {
          sections.push({
            ...currentSection,
            content: currentContent.join('\n').trim()
          });
        }
        
        // Start new section
        currentSection = {
          level: headerMatch[1].length,
          title: headerMatch[2].trim(),
          line: line
        };
        currentContent = [line];
      } else if (currentSection) {
        currentContent.push(line);
      }
    }
    
    // Add last section
    if (currentSection) {
      sections.push({
        ...currentSection,
        content: currentContent.join('\n').trim()
      });
    }
    
    return sections;
  }

  setupToolHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: 'search_codechecker_docs',
            description: 'Search CodeChecker documentation for specific topics, configurations, or usage patterns',
            inputSchema: {
              type: 'object',
              properties: {
                query: {
                  type: 'string',
                  description: 'Search query (keywords, topics, or specific features)'
                },
                section: {
                  type: 'string',
                  description: 'Optional: specific section to search (analyzer, web, tools, etc.)',
                  enum: ['analyzer', 'web', 'tools', 'all']
                }
              },
              required: ['query']
            }
          },
          {
            name: 'get_codechecker_document',
            description: 'Get the full content of a specific CodeChecker documentation file',
            inputSchema: {
              type: 'object',
              properties: {
                document_path: {
                  type: 'string',
                  description: 'Path to the document (e.g., "usage.md", "analyzer/user_guide.md")'
                }
              },
              required: ['document_path']
            }
          },
          {
            name: 'list_codechecker_docs',
            description: 'List available CodeChecker documentation files',
            inputSchema: {
              type: 'object',
              properties: {
                filter: {
                  type: 'string',
                  description: 'Optional filter for document types (analyzer, web, tools, etc.)'
                }
              }
            }
          }
        ]
      };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case 'search_codechecker_docs':
            return await this.handleSearchDocs(args);
          case 'get_codechecker_document':
            return await this.handleGetDocument(args);
          case 'list_codechecker_docs':
            return await this.handleListDocs(args);
          default:
            throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${name}`);
        }
      } catch (error) {
        if (error instanceof McpError) {
          throw error;
        }
        throw new McpError(ErrorCode.InternalError, `Tool execution failed: ${error.message}`);
      }
    });
  }

  async handleSearchDocs(args) {
    const { query, section } = args;
    
    if (!this.documentIndex) {
      throw new McpError(ErrorCode.InternalError, 'Document index not ready');
    }

    const results = [];
    const searchTerms = query.toLowerCase().split(/\s+/);
    
    for (const [docPath, doc] of Object.entries(this.documentIndex)) {
      // Filter by section if specified
      if (section && section !== 'all') {
        if (!docPath.startsWith(section + '/') && !docPath.includes('/' + section + '/')) {
          continue;
        }
      }
      
      const docContent = doc.content.toLowerCase();
      const docTitle = doc.title.toLowerCase();
      
      // Calculate relevance score
      let score = 0;
      let matchedSections = [];
      
      for (const term of searchTerms) {
        // Title matches are high value
        if (docTitle.includes(term)) score += 10;
        
        // Count content matches
        const matches = (docContent.match(new RegExp(term, 'g')) || []).length;
        score += matches;
        
        // Check section matches
        for (const section of doc.sections) {
          if (section.title.toLowerCase().includes(term) || 
              section.content.toLowerCase().includes(term)) {
            matchedSections.push({
              title: section.title,
              preview: this.getPreview(section.content, term, 200)
            });
          }
        }
      }
      
      if (score > 0) {
        results.push({
          document: docPath,
          title: doc.title,
          score,
          preview: this.getPreview(doc.content, searchTerms[0], 300),
          matchedSections: matchedSections.slice(0, 3) // Limit to top 3 sections
        });
      }
    }
    
    // Sort by relevance
    results.sort((a, b) => b.score - a.score);
    
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({
            query,
            section: section || 'all',
            total_results: results.length,
            results: results.slice(0, 10) // Top 10 results
          }, null, 2)
        }
      ]
    };
  }

  async handleGetDocument(args) {
    const { document_path } = args;
    
    if (!this.documentIndex) {
      throw new McpError(ErrorCode.InternalError, 'Document index not ready');
    }
    
    const doc = this.documentIndex[document_path];
    if (!doc) {
      throw new McpError(ErrorCode.InvalidParams, `Document not found: ${document_path}`);
    }
    
    return {
      content: [
        {
          type: 'text',
          text: `# ${doc.title}\n\n${doc.content}`
        }
      ]
    };
  }

  async handleListDocs(args) {
    const { filter } = args;
    
    if (!this.documentIndex) {
      throw new McpError(ErrorCode.InternalError, 'Document index not ready');
    }
    
    let docs = Object.entries(this.documentIndex).map(([path, doc]) => ({
      path,
      title: doc.title,
      size: doc.size,
      sections: doc.sections.length
    }));
    
    if (filter) {
      docs = docs.filter(doc => 
        doc.path.startsWith(filter + '/') || 
        doc.path.includes('/' + filter + '/') ||
        doc.title.toLowerCase().includes(filter.toLowerCase())
      );
    }
    
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({ 
            filter: filter || 'none',
            total_documents: docs.length,
            documents: docs 
          }, null, 2)
        }
      ]
    };
  }

  getPreview(content, searchTerm, maxLength = 200) {
    const index = content.toLowerCase().indexOf(searchTerm.toLowerCase());
    if (index === -1) {
      return content.substring(0, maxLength) + (content.length > maxLength ? '...' : '');
    }
    
    const start = Math.max(0, index - 50);
    const end = Math.min(content.length, start + maxLength);
    const preview = content.substring(start, end);
    
    return (start > 0 ? '...' : '') + preview + (end < content.length ? '...' : '');
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('CodeChecker MCP server running on stdio');
  }
}

// Run the server
if (require.main === module) {
  const server = new CodeCheckerMCPServer();
  server.run().catch(console.error);
}

module.exports = { CodeCheckerMCPServer };