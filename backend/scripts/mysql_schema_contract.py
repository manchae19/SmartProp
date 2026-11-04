"""Pure schema contract parser reused from the audited Phase A comparator. No SQL execution."""
import re

def split_items(text):
    items, start, depth, quote, i = [], 0, 0, '', 0
    while i < len(text):
        c = text[i]
        if quote:
            if c == '\\': i += 2; continue
            if c == quote:
                if i+1 < len(text) and text[i+1] == quote: i += 2; continue
                quote = ''
        elif c in "'\"`": quote = c
        elif c == '(': depth += 1
        elif c == ')': depth -= 1
        elif c == ',' and depth == 0:
            items.append(text[start:i].strip()); start = i+1
        i += 1
    items.append(text[start:].strip())
    return items

def canon(text):
    # Comparison aid, not a claim of full MySQL expression equivalence.
    text = text.replace('`','').lower()
    text = re.sub(r'\bboolean\b', 'tinyint(1)', text)
    return re.sub(r'\s+', ' ', text).strip()

def schema(text):
    text = re.sub(r'^\s*--[^\n]*', '', text, flags=re.M)
    tables = {}
    pattern = r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?`?(\w+)`?\s*\((.*?)\)\s*ENGINE\s*=\s*([^;]+);'
    for m in re.finditer(pattern, text, flags=re.I|re.S):
        tables[m[1]] = dict(items=split_items(m[2]), options=m[3].strip())
    for m in re.finditer(r'ALTER TABLE\s+`?(\w+)`?\s+(.*?);', text, flags=re.I|re.S):
        for item in split_items(m[2]):
            if re.match(r'^(?:ENABLE|DISABLE)\s+KEYS\b', item, re.I): continue
            if not re.match(r'^ADD\s+', item, re.I):
                raise ValueError('Unsupported ALTER in offline comparator: '+m[1])
            tables[m[1]]['items'].append(re.sub(r'^ADD\s+(?:COLUMN\s+)?', '', item, flags=re.I))
    return tables

def column_defs(table):
    cols = {}
    for item in table['items']:
        if re.match(r'^(?:CONSTRAINT|PRIMARY|UNIQUE|KEY|INDEX|CHECK|FOREIGN|SPATIAL|FULLTEXT)\b', item, re.I): continue
        m = re.match(r'`?(\w+)`?\s+(.*)', item, re.S)
        if m: cols[m[1]] = m[2]
    return cols

def column_contract(definition):
    value = canon(definition)
    m = re.match(r'(\w+(?:\([^)]*\))?(?: unsigned)?)', value)
    default = re.search(r'\bdefault\s+(\([^;]+\)|\w+\([^)]*\)|\x27[^\x27]*\x27|[^\s]+)', value)
    # Inline PK is implicitly NOT NULL. A missing default on a nullable column
    # is represented by MySQL as DEFAULT NULL.
    nullable = 'not null' not in value and 'primary key' not in value
    kind = m[1] if m else value
    default_value = default[1].strip() if default else 'null' if nullable else None
    if re.match(r'^(?:tinyint|smallint|int|bigint|decimal|double|float)\b',kind) and default_value is not None:
        default_value = {'false':'0','true':'1'}.get(default_value,default_value).strip("'")
    return dict(type=kind, nullable=nullable, default=default_value,
        auto_increment='auto_increment' in value,
        explicit_charset=(re.search(r'character set\s+(\w+)', value).group(1) if 'character set' in value else None),
        explicit_collation=(re.search(r'collate\s+(\w+)', value).group(1) if 'collate' in value else None),
        srid=(re.search(r'srid\s+(\d+)', value).group(1) if re.search(r'srid\s+(\d+)',value) else None))

def expand_version_comments(text):
    return re.sub(r'/\*!\d{5,6}\s*(.*?)\*/',r'\1',text,flags=re.S)

def parenthesized(text,start=None):
    start=text.index('(') if start is None else start
    depth=0;quote='';i=start
    while i<len(text):
        c=text[i]
        if quote:
            if c=='\\':i+=2;continue
            if c==quote:
                if i+1<len(text) and text[i+1]==quote:i+=2;continue
                quote=''
        elif c in "'\"`":quote=c
        elif c=='(':depth+=1
        elif c==')':
            depth-=1
            if depth==0:return text[start+1:i],i+1
        i+=1
    raise ValueError('Unbalanced SQL definition')

def columns_contract(table):
    result={}
    primary=[]
    for item in table['items']:
        if re.match(r'^PRIMARY KEY\b',item,re.I):primary=[x.strip(' `') for x in split_items(parenthesized(item)[0])]
    for name, definition in column_defs(table).items():
        definition=expand_version_comments(definition)
        value=column_contract(definition)
        if name in primary:value['nullable']=False
        # Preserve literal defaults while normalizing numeric/boolean spellings.
        d=re.search(r'\bDEFAULT\s+',definition,re.I)
        if d:
            tail=definition[d.end():]
            if tail.startswith('('):default=parenthesized(tail,0)[0].strip()
            else:
                m=re.match(r"'(?:''|\\.|[^'])*'|\w+\([^)]*\)|\S+",tail)
                default=m[0] if m else None
            if default is not None:
                numeric=bool(re.match(r'^(?:tinyint|smallint|int|bigint|decimal|double|float)\b',value['type']))
                value['default']=({'FALSE':'0','TRUE':'1'}.get(default.upper(),default).strip("'") if numeric else default)
        if value['default'] is not None and not value['default'].startswith("'"):
            value['default']=value['default'].lower()
        value['raw_definition']=definition
        result[name]=value
    return result

def names(text):
    return tuple(re.sub(r'\s+ASC\b','',x.replace('`','').strip(),flags=re.I).lower() for x in split_items(text))

def table_contract(table):
    columns=columns_contract(table);indexes={};fks={};checks={}
    for item in table['items']:
        item=expand_version_comments(item)
        fk=re.match(r'CONSTRAINT\s+`?(\w+)`?\s+FOREIGN KEY',item,re.I)
        if fk:
            local,end=parenthesized(item)
            ref=re.search(r'REFERENCES\s+`?(\w+)`?\s*\(',item[end:],re.I)
            target_start=end+ref.end()-1
            remote,remote_end=parenthesized(item,target_start)
            def action(kind):
                m=re.search(r'ON '+kind+r'\s+(RESTRICT|CASCADE|SET NULL|NO ACTION)',item[remote_end:],re.I)
                return 'RESTRICT' if not m or m[1].upper()=='NO ACTION' else m[1].upper()
            fks[fk[1]]=dict(columns=names(local),parent=ref[1],parent_columns=names(remote),on_delete=action('DELETE'),on_update=action('UPDATE'))
            continue
        ck=re.match(r'CONSTRAINT\s+`?(\w+)`?\s+CHECK\b',item,re.I)
        if ck:
            expression,end=parenthesized(item)
            checks[ck[1]]=dict(expression=expression,enforced=not bool(re.search(r'NOT\s+ENFORCED',item[end:],re.I)))
            continue
        pk=re.match(r'PRIMARY KEY\b',item,re.I)
        uq=re.match(r'CONSTRAINT\s+`?(\w+)`?\s+UNIQUE\b',item,re.I)
        ix=re.match(r'(?:(UNIQUE|SPATIAL|FULLTEXT)\s+)?(?:KEY|INDEX)\s+`?(\w+)`?',item,re.I)
        if pk or uq or ix:
            cols,end=parenthesized(item)
            key='PRIMARY' if pk else uq[1] if uq else ix[2]
            kind='UNIQUE' if pk or uq else ix[1].upper() if ix[1] else 'NORMAL'
            indexes[key]=dict(kind=kind,columns=names(cols),visible=not bool(re.search(r'\bINVISIBLE\b',item[end:],re.I)),
                method='SPATIAL' if kind=='SPATIAL' else 'FULLTEXT' if kind=='FULLTEXT' else 'BTREE')
        else:
            col=re.match(r'`?(\w+)`?\s+',item)
            if col and col[1] in columns and re.search(r'\bPRIMARY KEY\b',item,re.I):
                indexes['PRIMARY']=dict(kind='UNIQUE',columns=(col[1],),visible=True,method='BTREE')
    options=expand_version_comments(table['options'])
    engine=re.match(r'\w+',options)[0].lower()
    charset=re.search(r'(?:CHARSET|CHARACTER SET)\s*=\s*(\w+)',options,re.I)
    collate=re.search(r'COLLATE\s*=\s*(\w+)',options,re.I)
    return dict(columns=columns,indexes=indexes,foreign_keys=fks,checks=checks,
                engine=engine,charset=charset[1].lower() if charset else None,collation=collate[1].lower() if collate else None)

TOKEN=re.compile(r"\s*(?:(_[A-Za-z0-9]+)(?=')|('(?:''|\\.|[^'])*')|`([^`]+)`|([A-Za-z_]\w*)|(\d+(?:\.\d+)?)|(>=|<=|<>|!=|<=>|[=<>+*/%(),.-]))")

class CheckExpression:
    def __init__(self,text):
        self.tokens=[];i=0
        while i<len(text):
            m=TOKEN.match(text,i)
            if not m:
                if not text[i:].strip():break
                raise ValueError('Unsupported CHECK token: '+text[i:i+25])
            i=m.end()
            if m[1]:continue
            if m[2] is not None:self.tokens.append(('string',m[2]))
            elif m[3] is not None:self.tokens.append(('word',m[3].lower()))
            elif m[4] is not None:self.tokens.append(('word',m[4].lower()))
            elif m[5] is not None:self.tokens.append(('number',m[5]))
            else:self.tokens.append(('op',m[6]))
        self.i=0
    def peek(self):return self.tokens[self.i][1] if self.i<len(self.tokens) else ''
    def take(self,value=None):
        if self.i>=len(self.tokens):raise ValueError('Unexpected CHECK end')
        token=self.tokens[self.i]
        if value is not None and token[1]!=value:raise ValueError('Expected '+value+' got '+token[1])
        self.i+=1;return token
    def expr(self,min_priority=0):
        if self.peek() in ['not','+','-']:
            op=self.take()[1];left=(op,self.expr(3 if op=='not' else 7))
        elif self.peek()=='(':
            self.take('(');left=self.expr();self.take(')')
        else:
            token=self.take();left=token
            if token[0]=='word' and self.peek()=='(':
                self.take('(');args=[]
                if self.peek()!=')':
                    args.append(self.expr())
                    while self.peek()==',':self.take(',');args.append(self.expr())
                self.take(')');left=('call',token[1],tuple(args))
        priorities={'or':1,'and':2,'=':3,'!=':3,'<>':3,'<':3,'>':3,'<=':3,'>=':3,'is':3,'in':3,'between':3,'+':4,'-':4,'*':5,'/':5,'%':5}
        while True:
            next_op=self.peek()
            negated=next_op=='not' and self.i+1<len(self.tokens) and self.tokens[self.i+1][1] in ['in','between']
            priority=3 if negated else priorities.get(next_op,-1)
            if priority<min_priority:break
            op=self.take()[1]
            if negated:op=self.take()[1]
            if op=='between':
                low=self.expr(priority+1);self.take('and');high=self.expr(priority+1);left=('between',left,low,high)
            elif op=='is':
                negate=self.peek()=='not'
                if negate:self.take('not')
                right=self.take();left=('is_not' if negate else 'is',left,right)
            elif op=='in':
                self.take('(');values=[self.expr()]
                while self.peek()==',':self.take(',');values.append(self.expr())
                self.take(')');left=('in',left,tuple(values))
            else:
                right=self.expr(priority+1)
                if op in ['and','or']:
                    parts=[]
                    for operand in [left,right]:parts.extend(operand[1:] if operand[0]==op else [operand])
                    left=(op,*parts)
                else:left=(op,left,right)
            if negated:left=('not',left)
        return left
    def parse(self):
        result=self.expr()
        if self.i!=len(self.tokens):raise ValueError('Unconsumed CHECK expression: '+str(self.tokens[self.i:]))
        return result

def compare(expected,actual):
    differences=[];normalizations=[];check_count=0
    for name in sorted(expected.keys()-actual.keys()):differences.append(dict(severity='BLOCKER',table=name,issue='missing_table'))
    for name in sorted(actual.keys()-expected.keys()):differences.append(dict(severity='REVIEW',table=name,issue='extra_table'))
    for name in sorted(expected.keys()&actual.keys()):
        a,b=expected[name],actual[name]
        for kind in ['engine','charset','collation']:
            if a[kind] is not None and a[kind]!=b[kind]:differences.append(dict(severity='BLOCKER',table=name,kind=kind,expected=a[kind],actual=b[kind]))
        for column in sorted(a['columns'].keys()-b['columns'].keys()):differences.append(dict(severity='BLOCKER',table=name,column=column,issue='missing_column'))
        for column in sorted(b['columns'].keys()-a['columns'].keys()):differences.append(dict(severity='REVIEW',table=name,column=column,issue='extra_column'))
        for column in sorted(a['columns'].keys()&b['columns'].keys()):
            left,right=a['columns'][column],b['columns'][column]
            keys=['type','nullable','default','auto_increment']+['explicit_charset','explicit_collation','srid']
            for key in keys:
                if key in ['explicit_charset','explicit_collation','srid'] and left[key] is None:continue
                if left[key]!=right[key]:differences.append(dict(severity='BLOCKER',table=name,column=column,kind=key,expected=left[key],actual=right[key]))
        for kind in ['indexes','foreign_keys','checks']:
            for key in sorted(a[kind].keys()-b[kind].keys()):differences.append(dict(severity='BLOCKER',table=name,kind=kind,name=key,issue='missing'))
            for key in sorted(b[kind].keys()-a[kind].keys()):
                if kind=='indexes' and key in a['foreign_keys'] and b[kind][key]['columns']==a['foreign_keys'][key]['columns'] and b[kind][key]['kind']=='NORMAL':
                    normalizations.append(dict(table=name,index=key,reason='implicit_InnoDB_FK_supporting_index'))
                else:differences.append(dict(severity='REVIEW',table=name,kind=kind,name=key,issue='extra'))
            for key in sorted(a[kind].keys()&b[kind].keys()):
                left,right=a[kind][key],b[kind][key]
                if kind=='checks':
                    try:equal=CheckExpression(left['expression']).parse()==CheckExpression(right['expression']).parse() and left['enforced']==right['enforced'];check_count+=1
                    except ValueError as error:
                        differences.append(dict(severity='UNRESOLVED',table=name,kind=kind,name=key,reason=str(error)));continue
                else:equal=left==right
                if not equal:differences.append(dict(severity='BLOCKER',table=name,kind=kind,name=key,expected=left,actual=right))
    return differences,normalizations,check_count
