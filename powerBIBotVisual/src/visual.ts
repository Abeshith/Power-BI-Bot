/*
*  Power BI ChatBot Visual
*/
"use strict";

import powerbi from "powerbi-visuals-api";
import { BasicFilter, AdvancedFilter } from "powerbi-models";
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
        if (options.dataViews && options.dataViews.length > 0) {
            this.extractAndRegisterSchema(options.dataViews[0]);
        }
    }

    private extractAndRegisterSchema(dataView: any): void {
        try {
           console.log("DataView structure:", dataView);
           if (!dataView.table || !dataView.table.columns) {
               console.log("No table or columns in dataView, returning");
               return;
           }
           const columns: any = {};
           const categoricalCols: string[] = [];
           const numericCols: string[] = [];
           const dateCols: string[] = [];
            
           let tableName = "data";
           if (dataView.table.columns && dataView.table.columns.length > 0) {
               const firstCol = dataView.table.columns[0];
               if (firstCol.queryName) {
                   tableName = firstCol.queryName.split('.')[0];
               }
           }
            
           console.log(`Processing ${dataView.table.columns.length} columns`);

           for (const col of dataView.table.columns) {
               const colName = col.displayName || col.queryName;
               const colType = col.type?.primitiveType || "text";
               console.log(`Column: ${colName}, Type: ${colType}`);
               let colData: any = { type: colType, displayName: colName };

               if (dataView.table.rows) {
                   const colIndex = dataView.table.columns.indexOf(col);
                   const vals = dataView.table.rows.map((row: any) => row[colIndex]).filter((v: any) => v !== null && v !== undefined);
                   const isText = col.type?.text === true || col.type?.category != null;
                   const isNumeric = col.type?.numeric === true || col.type?.integer === true;
                   const isDate = col.type?.dateTime === true || col.type?.date === true;

                   if (isText) {
                       colData.distinct_values = [...new Set(vals as string[])];
                       categoricalCols.push(colName);
                   } else if (isNumeric) {
                       const numVals = vals.map((v: any) => Number(v)).filter((v: number) => !isNaN(v));
                       if (numVals.length > 0) {
                           colData.min = Math.min(...numVals);
                           colData.max = Math.max(...numVals);
                           colData.average = numVals.reduce((a: number, b: number) => a + b, 0) / numVals.length;
                           // For low-cardinality numeric cols (Year/Month/Day), expose distinct values
                           const uniqueNums = [...new Set(numVals)] as number[];
                           if (uniqueNums.length <= 500) {
                               colData.distinct_values = uniqueNums.sort((a, b) => a - b);
                           }
                       }
                       numericCols.push(colName);
                   } else if (isDate) {
                       const dateVals = vals.map((v: any) => new Date(v)).filter((v: Date) => !isNaN(v.getTime()));
                       if (dateVals.length > 0) {
                           colData.min_date = new Date(Math.min(...dateVals.map((d: Date) => d.getTime()))).toISOString();
                           colData.max_date = new Date(Math.max(...dateVals.map((d: Date) => d.getTime()))).toISOString();
                       }
                       dateCols.push(colName);
                   } else {
                       const strVals = vals.filter((v: any) => typeof v === "string");
                       if (strVals.length > 0) {
                           colData.distinct_values = [...new Set(strVals as string[])];
                           categoricalCols.push(colName);
                       }
                   }
               }

               columns[colName] = colData;
           }

           const schema = {
               tables: [tableName],
               columns: columns,
               categorical_columns: categoricalCols,
               numeric_columns: numericCols,
               date_columns: dateCols,
               table_name: tableName
           };
           console.log("Final schema to send:", schema);
           this.sendSchemaToBackend(schema);
       } catch (err) {
           console.log("Schema extraction error", err);
       }
    }

    private sendSchemaToBackend(schema: any): void {
        fetch(`${this.backendUrl}/api/schema/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(schema)
        });
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
        this.target.style.overflow = "hidden";

        const header = document.createElement("div");
        header.style.fontSize = "18px";
        header.style.fontWeight = "bold";
        header.style.marginBottom = "10px";
        header.style.color = "#333";
        header.textContent = "Power BI Query Assistant";

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
        welcomeTitle.textContent = "Welcome!";
        welcomeText.appendChild(welcomeTitle);
        welcomeText.appendChild(document.createElement("br"));
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
                       if (f.filterType === "advanced") {
                           const parts = f.conditions.map((c: any) => `${c.operator} ${c.value}`).join(" AND ");
                           return `${col} ${parts}`;
                       }
                       return `${col} = ${(f.values || []).join(', ')}`;
                   }).join(', ');
                   botMsg.textContent = `Bot: Applied ${data.filters.length} filter(s): ${filterSummary}`;
                    
                   console.log("Filters from backend:", JSON.stringify(data.filters, null, 2));
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
        if (!this.host || !filters || filters.length === 0) return;

        console.log(`Applying ${filters.length} filters`, JSON.stringify(filters));

        const allFilters: (BasicFilter | AdvancedFilter)[] = [];

        for (const f of filters) {
            if (!f.target?.table || !f.target?.column) continue;

            if (f.filterType === "advanced") {
                // Numeric / date comparison filter
                if (!f.conditions?.length) continue;
                allFilters.push(new AdvancedFilter(
                    { table: f.target.table, column: f.target.column },
                    f.logicalOperator || "And",
                    f.conditions  // [{ operator, value }]
                ));
            } else {
                // Categorical "In" filter
                if (!f.values?.length) continue;
                allFilters.push(new BasicFilter(
                    { table: f.target.table, column: f.target.column },
                    "In",
                    f.values
                ));
            }
        }

        if (allFilters.length === 0) return;

        this.host.applyJsonFilter(allFilters, "general", "filter", FilterAction.merge);
    }
}