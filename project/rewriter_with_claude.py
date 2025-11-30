def rewrite(self, method_name: str = "computeValue") -> str:
        """Rewrite the Java code keeping only executed lines"""
        method_start, method_end = self._find_method_bounds(method_name)
        
        if method_start is None:
            return '\n'.join(self.lines)
        
        # Find all control structure lines we need to keep
        required_control_lines = self._find_all_required_lines(method_start, method_end)
        
        result = []
        skip_depth = 0  # Track how many levels deep we are in skipped blocks
        brace_stack = []  # Track indentation for braces we need to close
        
        for i, line in enumerate(self.lines):
            actual_line_num = i + 1  # 1-indexed
            stripped = line.strip()
            
            # Outside method - keep everything
            if i < method_start or i > method_end:
                result.append(line)
                continue
            
            # Keep method signature
            if i == method_start:
                result.append(line)
                if '{' in line:
                    indent = len(line) - len(line.lstrip())
                    brace_stack.append(indent)
                continue
            
            # At method end, close remaining braces then output the method's closing brace
            if i == method_end:
                while len(brace_stack) > 1:  # Keep one for the method itself
                    indent = brace_stack.pop()
                    result.append(' ' * indent + '}')
                if brace_stack:  # Remove method brace from stack
                    brace_stack.pop()
                result.append(line)  # Use original closing brace
                continue
            
            # If we're skipping blocks
            if skip_depth > 0:
                # Track brace depth in skipped sections
                skip_depth += line.count('{')
                skip_depth -= line.count('}')
                continue
            
            # Check if this is an else clause
            if 'else' in line and (stripped.startswith('else') or '} else' in line):
                # We're not keeping else blocks
                # If the line has } else, we need to close the if block first
                if '} else' in line:
                    if brace_stack:
                        indent = brace_stack.pop()
                        result.append(' ' * indent + '}')
                
                # Now skip the else block
                skip_depth += line.count('{')
                skip_depth -= line.count('}')
                continue
            
            # Check if this is just a closing brace
            if stripped == '}':
                if brace_stack:
                    indent = brace_stack.pop()
                    result.append(' ' * indent + '}')
                continue
            
            # Check if we should keep this line
            should_keep = (actual_line_num in self.executed_lines or 
                          i in required_control_lines)
            
            if should_keep:
                result.append(line)
                # Track opening braces with their indentation
                # The closing brace should be at the same indentation as the line that opened the block
                if '{' in line:
                    indent = len(line) - len(line.lstrip())
                    brace_stack.append(indent)
        
        return '\n'.join(result)
import re
from typing import Set, List

class JavaRewriter:
    def __init__(self, java_code: str):
        self.lines = java_code.split('\n')
        self.executed_lines = set()
        
    def set_executed_lines(self, line_numbers: Set[int]):
        """Set which lines were executed (1-indexed)"""
        self.executed_lines = set(line_numbers)
    
    def _find_method_bounds(self, method_name: str) -> tuple:
        """Find start and end line of a method"""
        start = None
        brace_count = 0
        in_method = False
        
        for i, line in enumerate(self.lines):
            if method_name in line and '(' in line:
                start = i
                in_method = True
            
            if in_method:
                brace_count += line.count('{')
                brace_count -= line.count('}')
                
                if brace_count == 0 and start is not None:
                    return start, i
        
        return None, None
    
    def _is_control_structure(self, line: str) -> bool:
        """Check if line starts a control structure"""
        stripped = line.strip()
        keywords = ['if', 'for', 'while', 'do', 'switch', 'try', 'catch', 'finally']
        return any(stripped.startswith(kw + ' ') or stripped.startswith(kw + '(') 
                   for kw in keywords)
    
    def _find_enclosing_blocks(self, target_line: int, method_start: int) -> List[int]:
        """Find all control structure lines that enclose the target line"""
        enclosing = []
        brace_depth = 0
        control_stack = []  # Stack of (line_num, brace_depth_when_opened)
        
        for i in range(method_start + 1, target_line):
            line = self.lines[i]
            
            # Check if this is a control structure
            if self._is_control_structure(line):
                control_stack.append((i, brace_depth))
            
            # Update brace depth
            if '{' in line:
                brace_depth += 1
            if '}' in line:
                brace_depth -= 1
                # Pop control structures that just closed
                control_stack = [(ln, d) for ln, d in control_stack if d >= brace_depth]
        
        return [ln for ln, _ in control_stack]
    
    def _find_all_required_lines(self, method_start: int, method_end: int) -> Set[int]:
        """Find all lines needed to maintain structure for executed lines"""
        required = set()
        
        # For each executed line, find its enclosing control structures
        for line_num in self.executed_lines:
            zero_indexed = line_num - 1
            if method_start < zero_indexed <= method_end:
                enclosing = self._find_enclosing_blocks(zero_indexed, method_start)
                required.update(enclosing)
        
        return required
    
    def rewrite(self, method_name: str = "computeValue") -> str:
        """Rewrite the Java code keeping only executed lines"""
        method_start, method_end = self._find_method_bounds(method_name)
        
        if method_start is None:
            return '\n'.join(self.lines)
        
        # Find all control structure lines we need to keep
        required_control_lines = self._find_all_required_lines(method_start, method_end)
        
        result = []
        skip_depth = 0  # Track how many levels deep we are in skipped blocks
        brace_stack = []  # Track (indentation, line_num) for braces we need to close
        
        for i, line in enumerate(self.lines):
            actual_line_num = i + 1  # 1-indexed
            stripped = line.strip()
            
            # Outside method - keep everything
            if i < method_start or i > method_end:
                result.append(line)
                continue
            
            # Keep method signature
            if i == method_start:
                result.append(line)
                if '{' in line:
                    indent = len(line) - len(line.lstrip())
                    brace_stack.append((indent + 4, i))
                continue
            
            # If we're skipping blocks
            if skip_depth > 0:
                # Track brace depth in skipped sections
                skip_depth += line.count('{')
                skip_depth -= line.count('}')
                continue
            
            # Check if this is an else clause
            if 'else' in line and (stripped.startswith('else') or '} else' in line):
                # We're not keeping else blocks in this example
                # Mark that we should skip this block
                skip_depth += line.count('{')
                skip_depth -= line.count('}')
                
                # If the line has } else {, we need to output the closing }
                if '} else' in line or stripped.startswith('}'):
                    if brace_stack:
                        indent, _ = brace_stack.pop()
                        result.append(' ' * indent + '}')
                continue
            
            # Check if this is just a closing brace
            if stripped == '}':
                if brace_stack:
                    indent, _ = brace_stack.pop()
                    result.append(' ' * indent + '}')
                continue
            
            # Check if we should keep this line
            should_keep = (actual_line_num in self.executed_lines or 
                          i in required_control_lines)
            
            if should_keep:
                result.append(line)
                # Track opening braces with their indentation
                if '{' in line:
                    indent = len(line) - len(line.lstrip())
                    brace_stack.append((indent, i))
        
        # Add any remaining closing braces with proper indentation
        while brace_stack:
            indent, _ = brace_stack.pop()
            result.append(' ' * indent + '}')
        
        return '\n'.join(result)


# Example usage
if __name__ == "__main__":
    # Configuration
    input_file = "src/main/java/jpamb/cases/Extended.java"
    output_file = "src/main/java/jpamb/cases/Extended_rewritten.java"
    executed_lines = {4, 6, 8, 17}
    method_name = "computeValue"
    
    # Read input file
    with open(input_file, 'r') as f:
        java_code = f.read()
    
    # Rewrite code
    rewriter = JavaRewriter(java_code)
    rewriter.set_executed_lines(executed_lines)
    result = rewriter.rewrite(method_name)
    
    # Write output file
    with open(output_file, 'w') as f:
        f.write(result)
    
    print(f"Rewritten code saved to {output_file}")