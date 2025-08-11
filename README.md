# 🌊 Tornado MCP: AI-Powered Seismic Navigation System

> **The Future of Geophysical Data Interaction**: A production-ready agentic AI system that transforms natural language into precise seismic navigation commands on a 3D visualisation software, showcasing advanced LLM integration, coordinate transformation, and enterprise-grade system design.

## 🚀 **Why This Matters for the AI-First World**

This project demonstrates **cutting-edge agentic AI capabilities** that are reshaping how domain experts interact with complex software systems:

### **🎯 Agentic AI Innovation**
- **Natural Language → Domain Actions**: "Go to the gas area" automatically translates to `crossline 25431, inline 7878, depth 2231`
- **Multi-LLM Orchestration**: HTTP LLM primary with Gemini fallback, showcasing robust AI infrastructure
- **Context-Aware Intelligence**: Domain-specific geological knowledge dynamically loaded from configuration
- **Function Calling Mastery**: Seamless JSON-RPC command generation with parameter validation

## 🏗️ System Architecture

![Simplified Architecture](Simplified%20Architecture.png)

### **🏗️ Enterprise Systems Design**
- **Microservices Architecture**: Clean separation between NLP processing, coordinate transformation, and visualization control
- **Real-Time State Management**: SQLite-based command queuing with status tracking and error recovery
- **Configuration-Driven**: Linear coordinate mappings, transformation limits, and domain context via JSON
- **Production-Ready**: Comprehensive error handling, logging, fallback mechanisms, and graceful degradation

### **💡 Technical Excellence**
- **Coordinate Transformation Engine**: Bidirectional linear mapping between seismic coordinates and Cartesian space
- **Template System**: Dynamic HTML bookmark generation with parameter interpolation
- **Undo/Redo Architecture**: Complete state history management with 20-level deep undo stack
- **Multi-Provider LLM**: Transparent failover between HTTP endpoints and cloud APIs

---

## **🎬 What It Does**

Transform complex seismic navigation from this:
```
❌ Traditional: "Set X=159738, Y=75000, Z=1750, adjust gain to 2.5, change colormap to index 7"
```

To this:
```
✅ Natural: "Go to the gas area and make it brighter with rainbow colors"
```

The system automatically:
1. **Understands** geological terminology via domain context
2. **Translates** to precise coordinates using linear transformations  
3. **Executes** multiple commands with proper sequencing
4. **Provides** intelligent feedback with undo/redo capability

---

## **🔥 Key Innovations**

### **1. Intelligent Coordinate Transformation**
```python
# Configure once in config.json
"crossline_to_x": {
  "point1": {"crossline": 25519, "x": 159488},
  "point2": {"crossline": 25599, "x": 159988}
}

# Use everywhere with natural language
"Move to crossline 25559" → X=159738 (automatic integer conversion)
```

### **2. Domain Context Intelligence**
```json
{
  "domain_context": "When user asks to go to area with a lot of gas, move to crossline 25431, depth 2231, inline 7878..."
}
```

### **3. Multi-LLM Resilience**
```
HTTP LLM (Primary) → Gemini API (Fallback) → Graceful Error Handling
```

### **4. Real-Time Command Processing**
```
Natural Language → JSON-RPC → SQLite Queue → Tornado Execution → State Feedback
```

---

## **🏗️ System Architecture**

### **Microservices Design Pattern**
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   NLP End       │    │   Shared Utils   │    │  Tornado End    │
│  (Windows)      │    │                  │    │   (Linux)       │
├─────────────────┤    ├──────────────────┤    ├─────────────────┤
│ • Gemini Parser │    │ • Config Loader  │    │ • Bookmark Eng. │
│ • HTTP LLM      │◄──►│ • Coord Mapper   │◄──►│ • Seismic Nav.  │
│ • Chat Terminal │    │ • Context Loader │    │ • State Manager │
│ • Command Queue │    │ • Limits Loader  │    │ • Command Proc. │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌──────────────────┐
                    │   SQLite DB      │
                    │ • Command Queue  │
                    │ • State Storage  │
                    │ • Status Tracking│
                    └──────────────────┘
```

### **📁 Project Structure**
```
tornado-mcp/
├── 🔧 config.json              # Coordinate mappings & paths
├── 🧠 context.json             # Domain knowledge base
├── ⚙️ .env                     # LLM provider configuration
├── 📋 INSTRUCTIONS.md          # Quick start guide
│
├── 📁 src/
│   ├── 📁 nlp_end/            # Natural Language Processing
│   │   ├── 📁 nlp/            # • Gemini command parser
│   │   └── 📁 terminal/       # • Interactive chat terminal
│   │
│   ├── 📁 tornado_end/        # Tornado Integration
│   │   ├── 📁 core/           # • Bookmark engine v2
│   │   │                      # • Seismic navigation
│   │   │                      # • Coordinate transformation
│   │   └── tornado_listener.py # • Command processor
│   │
│   └── 📁 shared/             # Shared Components
│       ├── 📁 database/       # • SQLite management
│       ├── 📁 llm/            # • Multi-LLM provider
│       ├── 📁 protocols/      # • JSON-RPC protocols
│       └── 📁 utils/          # • Config & context loaders
│
├── 📁 data/                   # Templates & Bookmarks
│   ├── 📁 bookmarks/         # • Generated bookmarks
│   └── 📁 templates/         # • HTML templates
│
└── 📁 database/              # SQLite Database Files
    └── tornado_mcp.db        # • Command queue & state
```

---

## **⚡ Quick Start**

> **Detailed setup instructions available in [INSTRUCTIONS.md](INSTRUCTIONS.md)**

### **1. Natural Language Navigation**
```bash
# Start the AI assistant
python src/nlp_end/main.py

# Natural language commands:
🎯 seismic> go to the gas area
✅ Moving to crossline 25431, inline 7878, depth 2231

🎯 seismic> make it brighter and use rainbow colors  
✅ Increasing gain by 4dB and changing to rainbow colormap

🎯 seismic> undo that
✅ Undoing last action - reverted to previous state
```

### **2. Coordinate Transformation**
```python
from shared.utils.coordinate_mapper import get_coordinate_mapper

mapper = get_coordinate_mapper()

# Seismic → Cartesian
x, y, z = mapper.seismic_to_cartesian(crossline=25559, inline=5000, depth=1750)
# Result: X=159738, Y=62488, Z=1750 (all integers)

# Cartesian → Seismic  
crossline, inline, depth = mapper.cartesian_to_seismic(x=159738, y=62488, z=1750)
# Result: crossline=25559, inline=5000, depth=1750
```

### **3. Domain Context Configuration**
```json
// context.json
{
  "domain_context": "When user asks to go to area with a lot of gas, move to crossline 25431, depth 2231, inline 7878. When user asks to go to the fault zone, move to crossline 25550, inline 5000, depth 3000..."
}
```

### **4. Multi-LLM Configuration**
```env
# .env
DEFAULT_LLM_PROVIDER=http_llm
HTTP_LLM_SERVER_URL=your-http-llm
FALLBACK_LLM_PROVIDERS=gemini
GEMINI_API_KEY=your_gemini_api_key
```

---

## **🎯 Core Features**

### **Natural Language Understanding**
- **Geological Terminology**: Understands "gas area", "fault zone", "reservoir", "salt dome"
- **Spatial Commands**: "move left", "go deeper", "zoom in", "rotate right"
- **Display Controls**: "make it brighter", "use rainbow colors", "increase contrast"
- **Navigation**: "go to crossline 25559", "move to inline 5000", "depth 1750"

### **Intelligent Coordinate System**
- **Seismic ↔ Cartesian**: Bidirectional linear transformation with integer precision
- **Configurable Mappings**: Two-point linear interpolation via config.json
- **Domain-Aware**: Crossline/Inline/Depth instead of X/Y/Z terminology
- **Validation**: Range checking and type enforcement

### **Multi-LLM Infrastructure**
- **Primary Provider**: HTTP LLM for fast, local processing
- **Fallback Provider**: Gemini API for reliability
- **Function Calling**: JSON-RPC command generation
- **Error Recovery**: Graceful degradation and retry logic

### **State Management**
- **Command Queue**: SQLite-based asynchronous processing
- **History Tracking**: 20-level undo/redo with state snapshots
- **Real-Time Sync**: Live state updates between components
- **Status Monitoring**: Command execution tracking and error reporting

---

## **🛠️ Technical Implementation**

### **Coordinate Transformation Mathematics**
```python
# Linear transformation: cartesian = slope * seismic + intercept
slope = (x2 - x1) / (crossline2 - crossline1)
intercept = x1 - (slope * crossline1)

# Example with actual values:
# crossline 25519 → X 159488, crossline 25599 → X 159988
# slope = (159988 - 159488) / (25599 - 25519) = 6.25
# X = 6.25 * crossline + (-0.125)
```

### **LLM Provider Architecture**
```python
class LLMFactory:
    def get_available_provider(self):
        # Try default provider (HTTP LLM)
        if default.is_available():
            return default
        
        # Fallback to Gemini
        for provider in fallback_providers:
            if provider.is_available():
                return provider
        
        return None  # Graceful degradation
```

### **Command Processing Pipeline**
```
1. Natural Language Input
2. LLM Function Calling (JSON-RPC)
3. Parameter Validation & Transformation
4. SQLite Command Queue
5. Tornado Execution
6. State Update & Feedback
```

---

## **🚀 Getting Started**

### **Prerequisites**
- Python 3.6+ (Linux) / Python 3.8+ (Windows)
- SQLite3
- Access to HTTP LLM endpoint OR Gemini API key
- Tornado software (for production use)

### **Installation**
```bash
# Clone repository
cd tornado-mcp

# Install dependencies
pip install -r win-requirements.txt and linux-requirements into .win-venv and .linux-venv
but during usage, DO NOT activate environments (this is some 'hacking' over security)

# Configure environment
cp .env.example .env
# Edit .env with your LLM provider settings

# Configure coordinate mappings
# Edit config.json with your seismic survey coordinates

# Add domain knowledge
# Edit context.json with geological feature locations
```

### **Usage**
```bash
# Start NLP terminal (Windows)
python src/nlp_end/main.py

# Start Tornado listener (Linux, inside Tornado)
python src/tornado_end/tornado_listener.py
```


## **🔒 Security & Reliability**

### **Security Measures**
- **Input Validation**: Parameter range checking and type enforcement
- **SQL Injection Prevention**: Parameterized queries throughout
- **API Key Management**: Environment-based configuration
- **Error Sanitization**: Safe error messages without sensitive data

### **Reliability Features**
- **Graceful Degradation**: System continues with reduced functionality
- **Automatic Retry**: Configurable retry logic for failed operations
- **State Recovery**: Persistent state storage and recovery
- **Comprehensive Logging**: Detailed logging for debugging and monitoring


## **📈 Business Value**

### **For Geophysicists**
- **10x Faster Navigation**: Natural language vs. manual coordinate entry
- **Reduced Errors**: Automated coordinate transformation eliminates mistakes
- **Domain Expertise**: System understands geological terminology
- **Intuitive Interface**: No need to learn complex software commands

### **For Organizations**
- **Productivity Gains**: Faster seismic interpretation workflows
- **Training Reduction**: Minimal learning curve for new users
- **Standardization**: Consistent navigation patterns across teams
- **Integration Ready**: API-first design for enterprise integration

---

## **🎓 Learning Outcomes**

This project demonstrates mastery of:

- **Agentic AI Systems**: Multi-LLM orchestration with intelligent fallbacks
- **Domain-Specific AI**: Context-aware natural language processing
- **Microservices Architecture**: Distributed system design and communication
- **Real-Time Systems**: Asynchronous processing and state management
- **Mathematical Modeling**: Linear transformations and coordinate systems
- **Enterprise Software**: Production-ready error handling and monitoring
- **API Design**: RESTful and JSON-RPC protocol implementation
- **Database Design**: Efficient queuing and state storage patterns

---
