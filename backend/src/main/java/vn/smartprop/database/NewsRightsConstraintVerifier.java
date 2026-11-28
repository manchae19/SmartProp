package vn.smartprop.database;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import org.springframework.jdbc.core.JdbcTemplate;

/** Verifies the exact V28 CHECK invariant from MySQL metadata before enabling News. */
public final class NewsRightsConstraintVerifier {
    public static final String CONSTRAINT = "ck_news_sources_approved_reference";
    private static final Expr EXPECTED = new Or(
        new Compare("rights_review_status", "<>", "APPROVED"),
        new And(new IsNotNull("rights_reference"), new RegexLike("rights_reference", "[^[:space:]]"))
    );

    private NewsRightsConstraintVerifier() {}

    public static int countNamed(JdbcTemplate jdbc) {
        return jdbc.queryForObject("SELECT COUNT(*) FROM information_schema.table_constraints WHERE constraint_schema=DATABASE() AND constraint_name=?", Integer.class, CONSTRAINT);
    }

    public static void requireValid(JdbcTemplate jdbc) {
        String schema = jdbc.queryForObject("SELECT DATABASE()", String.class);
        if (schema == null || schema.isBlank()) throw new IllegalStateException("V28 constraint schema is unknown.");
        List<Map<String, Object>> rows = jdbc.queryForList(
            "SELECT tc.table_name, tc.constraint_type, tc.enforced, cc.check_clause "
                + "FROM information_schema.table_constraints tc "
                + "JOIN information_schema.check_constraints cc "
                + "ON cc.constraint_schema=tc.constraint_schema AND cc.constraint_name=tc.constraint_name "
                + "WHERE tc.constraint_schema=? AND tc.constraint_name=?",
            schema, CONSTRAINT);
        if (rows.size() != 1) throw new IllegalStateException("Required V28 rights constraint is missing or ambiguous.");
        Map<String, Object> row = rows.getFirst();
        if (!"news_sources".equalsIgnoreCase(String.valueOf(row.get("table_name")))
                || !"CHECK".equalsIgnoreCase(String.valueOf(row.get("constraint_type")))
                || !"YES".equalsIgnoreCase(String.valueOf(row.get("enforced"))))
            throw new IllegalStateException("Required V28 rights constraint is attached to the wrong table, has the wrong type, or is unenforced.");
        String clause = String.valueOf(row.get("check_clause"));
        try {
            if (!EXPECTED.equals(new Parser(clause).parse()))
                throw new IllegalStateException("Required V28 rights constraint has an incorrect definition.");
        } catch (IllegalArgumentException e) {
            throw new IllegalStateException("Required V28 rights constraint has an invalid definition.", e);
        }
    }

    private sealed interface Expr permits Or, And, Compare, IsNotNull, RegexLike {}
    private record Or(Expr left, Expr right) implements Expr {}
    private record And(Expr left, Expr right) implements Expr {}
    private record Compare(String column, String operator, String literal) implements Expr {}
    private record IsNotNull(String column) implements Expr {}
    private record RegexLike(String column, String pattern) implements Expr {}

    /** Small strict parser for the approved invariant; unknown syntax fails closed. */
    private static final class Parser {
        private final List<Token> tokens = new ArrayList<>();
        private int at;
        Parser(String source) { lex(source); }
        Expr parse() {
            Expr result = or();
            if (at != tokens.size()) throw invalid();
            return result;
        }
        private Expr or() {
            Expr result = and();
            while (takeWord("or")) result = new Or(result, and());
            return result;
        }
        private Expr and() {
            Expr result = atom();
            while (takeWord("and")) result = new And(result, atom());
            return result;
        }
        private Expr atom() {
            if (take("(")) { Expr nested = or(); require(")"); return nested; }
            if (peekWord("regexp_like")) {
                at++;
                require("(");
                String column = identifier();
                require(",");
                skipCharsetIntroducer();
                String pattern = string();
                require(")");
                return new RegexLike(column, pattern);
            }
            String column = identifier();
            if (takeWord("is")) {
                requireWord("not");
                requireWord("null");
                return new IsNotNull(column);
            }
            String operator = next().value;
            if (!operator.equals("<>")) throw invalid();
            skipCharsetIntroducer();
            return new Compare(column, operator, string());
        }
        private String identifier() {
            Token token = next();
            if (!token.word) throw invalid();
            return token.value.toLowerCase(Locale.ROOT);
        }
        private void skipCharsetIntroducer() {
            if (peekWord("_ascii") || peekWord("_utf8mb4") || peekWord("_utf8mb3")
                    || peekWord("_utf8") || peekWord("_binary")) at++;
        }
        private String string() {
            Token token = next();
            if (!token.string) throw invalid();
            return token.value;
        }
        private void requireWord(String value) { if (!takeWord(value)) throw invalid(); }
        private boolean takeWord(String value) { if (peekWord(value)) { at++; return true; } return false; }
        private boolean peekWord(String value) {
            return at < tokens.size() && tokens.get(at).word && tokens.get(at).value.equalsIgnoreCase(value);
        }
        private void require(String value) { if (!take(value)) throw invalid(); }
        private boolean take(String value) {
            if (at < tokens.size() && tokens.get(at).value.equals(value)) { at++; return true; }
            return false;
        }
        private Token next() { if (at >= tokens.size()) throw invalid(); return tokens.get(at++); }
        private IllegalArgumentException invalid() { return new IllegalArgumentException("Unsupported CHECK expression."); }
        private void lex(String sql) {
            for (int i = 0; i < sql.length();) {
                char c = sql.charAt(i);
                if (Character.isWhitespace(c)) { i++; continue; }
                if (c == '\\' && i + 1 < sql.length() && sql.charAt(i + 1) == '\'') {
                    i++;
                    c = '\'';
                }
                if (c == '\'') {
                    StringBuilder value = new StringBuilder();
                    i++;
                    boolean closed = false;
                    while (i < sql.length()) {
                        char ch = sql.charAt(i++);
                        if (ch == '\'' && i < sql.length() && sql.charAt(i) == '\'') { value.append('\''); i++; }
                        else if (ch == '\'') { closed = true; break; }
                        else if (ch == '\\' && i < sql.length() && sql.charAt(i) == '\'') { closed = true; i++; break; }
                        else if (ch == '\\') throw invalid();
                        else value.append(ch);
                    }
                    if (!closed) throw invalid();
                    tokens.add(new Token(value.toString(), false, true));
                    continue;
                }
                if (c == '`') {
                    StringBuilder value = new StringBuilder();
                    i++;
                    boolean closed = false;
                    while (i < sql.length()) {
                        char ch = sql.charAt(i++);
                        if (ch == '`' && i < sql.length() && sql.charAt(i) == '`') { value.append('`'); i++; }
                        else if (ch == '`') { closed = true; break; }
                        else value.append(ch);
                    }
                    if (!closed) throw invalid();
                    tokens.add(new Token(value.toString(), true, false));
                    continue;
                }
                if (Character.isLetter(c) || c == '_') {
                    int start = i++;
                    while (i < sql.length() && (Character.isLetterOrDigit(sql.charAt(i)) || sql.charAt(i) == '_' || sql.charAt(i) == '$')) i++;
                    tokens.add(new Token(sql.substring(start, i), true, false));
                    continue;
                }
                if (i + 1 < sql.length() && (sql.startsWith("<>", i) || sql.startsWith("!=", i))) {
                    tokens.add(new Token(sql.substring(i, i + 2), false, false));
                    i += 2;
                    continue;
                }
                if ("(),".indexOf(c) >= 0 || c == '=') {
                    tokens.add(new Token(String.valueOf(c), false, false));
                    i++;
                    continue;
                }
                throw invalid();
            }
        }
    }
    private record Token(String value, boolean word, boolean string) {}
}
