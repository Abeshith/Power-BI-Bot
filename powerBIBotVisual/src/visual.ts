/*
*  Power BI ChatBot Visual
*/
"use strict";

import powerbi from "powerbi-visuals-api";
import { BasicFilter } from "powerbi-models";
import "./../style/visual.less";

import VisualConstructorOptions = powerbi.extensibility.visual.VisualConstructorOptions;
import VisualUpdateOptions = powerbi.extensibility.visual.VisualUpdateOptions;
import IVisual = powerbi.extensibility.visual.IVisual;
import IVisualHost = powerbi.extensibility.visual.IVisualHost;
import FilterAction = powerbi.FilterAction;

export class Visual implements IVisual {
    private target: HTMLElement;
    private host: IVisualHost;
    private backendUrl: string = "http://localhost:8000";
    private rendered: boolean = false;

    constructor(options: VisualConstructorOptions) {
        this.target = options.element;
        this.host = options.host;
        this.renderChatbot();
    }

    public update(options: VisualUpdateOptions) {
        if (!this.rendered) {
            this.renderChatbot();
        }
    }

    public getFormattingModel(): powerbi.visuals.FormattingModel {
        return { cards: [] };
    }

    private renderChatbot(): void {
        while (this.target.firstChild) {
            this.target.removeChild(this.target.firstChild);
        }
        this.target.style.display = "flex";
        this.target.style.flexDirection = "column";
        this.target.style.height = "100%";
        this.target.style.padding = "10px";
        this.target.style.fontFamily = "Arial, sans-serif";
        this.target.style.backgroundColor = "#f5f5f5";

        // Header
        const header = document.createElement("div");
        header.style.fontSize = "18px";
        header.style.fontWeight = "bold";
        header.style.marginBottom = "10px";
        header.style.color = "#333";
        header.textContent = "🤖 Power BI Query Assistant";

        // Input area
        const inputContainer = document.createElement("div");
        inputContainer.style.display = "flex";
        inputContainer.style.gap = "8px";
        inputContainer.style.marginBottom = "10px";

        const input = document.createElement("input");
        input.type = "text";
        input.placeholder = "Ask a question about your data...";
        input.style.flex = "1";
        input.style.padding = "10px";
        input.style.border = "1px solid #ccc";
        input.style.borderRadius = "4px";

        const button = document.createElement("button");
        button.textContent = "Send";
        button.style.padding = "10px 20px";
        button.style.backgroundColor = "#0078d4";
        button.style.color = "white";
        button.style.border = "none";
        button.style.borderRadius = "4px";
        button.style.cursor = "pointer";

        inputContainer.appendChild(input);
        inputContainer.appendChild(button);

        // Messages area
        const messagesArea = document.createElement("div");
        messagesArea.style.flex = "1";
        messagesArea.style.overflowY = "auto";
        messagesArea.style.border = "1px solid #ddd";
        messagesArea.style.padding = "10px";
        messagesArea.style.borderRadius = "4px";
        messagesArea.style.backgroundColor = "white";
        messagesArea.style.marginBottom = "10px";

        const welcome = document.createElement("div");
        welcome.style.padding = "10px";
        welcome.style.backgroundColor = "#e8f4f8";
        welcome.style.borderRadius = "4px";
        welcome.style.marginBottom = "10px";
        welcome.style.lineHeight = "1.5";
         
        const welcomeText = document.createElement("div");
        const welcomeTitle = document.createElement("strong");
        welcomeTitle.textContent = "Welcome! 👋";
        welcomeText.appendChild(welcomeTitle);
         
        const br1 = document.createElement("br");
        welcomeText.appendChild(br1);
         
        const text1 = document.createTextNode("Type your question to filter your dashboard:");
        welcomeText.appendChild(text1);
         
        welcome.appendChild(welcomeText);
        messagesArea.appendChild(welcome);

        // Send button handler
        button.onclick = () => this.handleQuery(input.value, messagesArea, input, button);
        input.onkeypress = (e) => {
            if (e.key === "Enter") {
                this.handleQuery(input.value, messagesArea, input, button);
            }
        };

        this.target.appendChild(header);
        this.target.appendChild(inputContainer);
        this.target.appendChild(messagesArea);
        this.rendered = true;
    }

    private async handleQuery(query: string, messagesArea: HTMLElement, input: HTMLInputElement, button: HTMLButtonElement) {
       if (!query.trim()) return;

       const userMsg = document.createElement("div");
       userMsg.style.padding = "8px";
       userMsg.style.marginBottom = "8px";
       userMsg.style.backgroundColor = "#e3f2fd";
       userMsg.style.borderRadius = "4px";
       userMsg.textContent = "You: " + query;
       messagesArea.appendChild(userMsg);

       input.value = "";
       button.disabled = true;
       button.textContent = "Processing...";

       try {
           const response = await fetch(`${this.backendUrl}/api/parse`, {
               method: "POST",
               headers: { "Content-Type": "application/json" },
               body: JSON.stringify({ query, apply_filters: true }),
           });

           if (response.ok) {
               const data = await response.json();
               const botMsg = document.createElement("div");
               botMsg.style.padding = "8px";
               botMsg.style.marginBottom = "8px";
               botMsg.style.backgroundColor = "#f0f0f0";
               botMsg.style.borderRadius = "4px";
                
               if (data.filters && data.filters.length > 0) {
                   const filterSummary = data.filters.map((f: any) => {
                       const col = f.target?.column || 'filter';
                       const values = f.conditions?.[0]?.values || [];
                       return `${col} = ${values.join(', ')}`;
                   }).join(', ');
                   botMsg.textContent = `Bot: Applied ${data.filters.length} filter(s): ${filterSummary}\n\n⚠️ NOTE: Filters are being sent. If charts don't update, the dashboard may need a different configuration.`;
                    
                   // Try to apply filters
                   this.applyFiltersToVisuals(data.filters);
               } else {
                   botMsg.textContent = "Bot: Query processed (no filters applied)";
               }
               messagesArea.appendChild(botMsg);
           } else {
               const botMsg = document.createElement("div");
               botMsg.style.color = "red";
               botMsg.style.padding = "8px";
               botMsg.textContent = "Bot: Error - " + response.statusText;
               messagesArea.appendChild(botMsg);
           }
       } catch (err: any) {
           const botMsg = document.createElement("div");
           botMsg.style.color = "red";
           botMsg.style.padding = "8px";
           botMsg.textContent = `Bot: Backend unavailable (${this.backendUrl})`;
           messagesArea.appendChild(botMsg);
       }

       button.disabled = false;
       button.textContent = "Send";
       messagesArea.scrollTop = messagesArea.scrollHeight;
    }

    private applyFiltersToVisuals(filters: any[]): void {
       console.log("🔍 Attempting to apply filters...");
       console.log("Filters:", JSON.stringify(filters, null, 2));
         
       if (!this.host) {
           console.error("❌ Host is null - cannot apply filters");
           return;
       }

       for (let i = 0; i < filters.length; i++) {
           const filter = filters[i];
           const tableName = filter.target?.table || "hospital_data";
           const columnName = filter.target?.column;
           const values = filter.conditions?.[0]?.values || [];

           console.log(`\nFilter ${i}:`);
           console.log(`  Table: ${tableName}`);
           console.log(`  Column: ${columnName}`);
           console.log(`  Values: ${JSON.stringify(values)}`);

           if (!columnName || values.length === 0) continue;

           try {
               // Power BI requires column reference in format: Table[Column]
               const columnRef = `${tableName}[${columnName}]`;
                
               const basicFilter = new BasicFilter(
                   {
                       table: tableName,
                       column: columnName
                   },
                   "In",
                   values
               );

               console.log(`  Column reference: ${columnRef}`);
               console.log(`  Calling applyJsonFilter...`);
               this.host.applyJsonFilter(basicFilter, "general", "filter", FilterAction.merge);
               console.log(`  ✅ Filter call succeeded`);
           } catch (err: any) {
               console.error(`  ❌ Filter failed:`, String(err));
           }
       }
    }
}