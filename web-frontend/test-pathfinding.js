// test-pathfinding.js - Simple test for A* pathfinding
import { aStar } from './src/utils/pathfinding/aStar.ts';

// Test basic A* functionality
console.log('Testing A* Pathfinding...');

// Simple 3x3 grid with no obstacles
const grid = [
    [false, false, false],
    [false, false, false],
    [false, false, false],
];

const result = aStar({ x: 0, y: 0 }, { x: 2, y: 2 }, grid, { width: 3, height: 3 });

console.log('Path found:', result.found);
console.log('Path:', result.path);

if (result.found && result.path.length > 0) {
    console.log('✅ A* algorithm is working!');
} else {
    console.log('❌ A* algorithm failed');
}