// test-pathfinding.js - Simple test for A* pathfinding
import { aStarSpatial } from './src/utils/pathfinding/aStar.ts';

// Test basic A* functionality
console.log('Testing A* Pathfinding...');

const nodes = new Map();
nodes.set("0,0", { id: "0,0", x: 0, y: 0, neighbors: [{ nodeId: "1,0", distance: 1, direction: 'horizontal' }, { nodeId: "0,1", distance: 1, direction: 'vertical' }] });
nodes.set("1,0", { id: "1,0", x: 1, y: 0, neighbors: [{ nodeId: "0,0", distance: 1, direction: 'horizontal' }, { nodeId: "2,0", distance: 1, direction: 'horizontal' }] });
nodes.set("2,0", { id: "2,0", x: 2, y: 0, neighbors: [{ nodeId: "1,0", distance: 1, direction: 'horizontal' }, { nodeId: "2,1", distance: 1, direction: 'vertical' }] });

nodes.set("0,1", { id: "0,1", x: 0, y: 1, neighbors: [{ nodeId: "0,0", distance: 1, direction: 'vertical' }, { nodeId: "0,2", distance: 1, direction: 'vertical' }] });
nodes.set("2,1", { id: "2,1", x: 2, y: 1, neighbors: [{ nodeId: "2,0", distance: 1, direction: 'vertical' }, { nodeId: "2,2", distance: 1, direction: 'vertical' }] });

nodes.set("0,2", { id: "0,2", x: 0, y: 2, neighbors: [{ nodeId: "0,1", distance: 1, direction: 'vertical' }, { nodeId: "1,2", distance: 1, direction: 'horizontal' }] });
nodes.set("1,2", { id: "1,2", x: 1, y: 2, neighbors: [{ nodeId: "0,2", distance: 1, direction: 'horizontal' }, { nodeId: "2,2", distance: 1, direction: 'horizontal' }] });
nodes.set("2,2", { id: "2,2", x: 2, y: 2, neighbors: [{ nodeId: "1,2", distance: 1, direction: 'horizontal' }, { nodeId: "2,1", distance: 1, direction: 'vertical' }] });

const result = aStarSpatial("0,0", "2,2", nodes);

console.log('Path found:', result.found);
console.log('Path:', result.path);

if (result.found && result.path.length > 0) {
    console.log('✅ A* algorithm is working!');
} else {
    console.log('❌ A* algorithm failed');
}