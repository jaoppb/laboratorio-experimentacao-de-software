<?php
// Cria o estudante sintético, o quiz e 5 questões multichoice no curso "lab05"; idempotente.
// Executado dentro do contêiner: php < semear_dados.php (senha em ALUNO_SENHA).
define('CLI_SCRIPT', true);
require '/var/www/html/config.php';
require_once $CFG->libdir . '/enrollib.php';
require_once $CFG->dirroot . '/course/modlib.php';
require_once $CFG->dirroot . '/question/engine/bank.php';
require_once $CFG->dirroot . '/question/editlib.php';
require_once $CFG->dirroot . '/user/lib.php';
require_once $CFG->dirroot . '/mod/quiz/locallib.php';

if (!getenv('ALUNO_SENHA')) {
    fwrite(STDERR, "Defina ALUNO_SENHA.\n");
    exit(1);
}
\core\session\manager::set_user(get_admin());
$curso = $DB->get_record('course', ['shortname' => 'lab05'], '*', MUST_EXIST);

if (!$DB->record_exists('user', ['username' => 'aluno_teste_1'])) {
    $usuario = (object) [
        'username' => 'aluno_teste_1',
        'password' => getenv('ALUNO_SENHA'),
        'firstname' => 'Aluno',
        'lastname' => 'Teste',
        'email' => 'aluno_teste_1@example.invalid',
        'confirmed' => 1,
        'auth' => 'manual',
        'mnethostid' => $CFG->mnet_localhost_id,
    ];
    $id = user_create_user($usuario, true, false);
    $papel = $DB->get_field('role', 'id', ['shortname' => 'student'], MUST_EXIST);
    enrol_try_internal_enrol($curso->id, $id, $papel);
}

if (!$DB->record_exists('quiz', ['course' => $curso->id])) {
    $modulo = $DB->get_record('modules', ['name' => 'quiz'], '*', MUST_EXIST);
    $info = (object) [
        'modulename' => 'quiz', 'module' => $modulo->id, 'course' => $curso->id,
        'section' => 1, 'visible' => 1, 'name' => 'Quiz piloto', 'introeditor' => ['text' => '', 'format' => FORMAT_HTML, 'itemid' => 0],
        'timeopen' => 0, 'timeclose' => 0, 'timelimit' => 0, 'grade' => 10, 'sumgrades' => 0,
        'preferredbehaviour' => 'deferredfeedback', 'attempts' => 0, 'grademethod' => 1, 'quizpassword' => '',
        'questionsperpage' => 0,
    ];
    create_module($info);
}

$quiz = $DB->get_record('quiz', ['course' => $curso->id], '*', MUST_EXIST);
$cm = get_coursemodule_from_instance('quiz', $quiz->id, $curso->id, false, MUST_EXIST);
$quiz->cmid = $cm->id;

$alvo_questoes = 5;
$transaction = $DB->start_delegated_transaction();
if ((int) $quiz->questionsperpage !== 0) {
    $DB->set_field('quiz', 'questionsperpage', 0, ['id' => $quiz->id]);
    $quiz->questionsperpage = 0;
    if ($DB->count_records('quiz_slots', ['quizid' => $quiz->id]) > 0) {
        quiz_repaginate_questions($quiz->id, 0);
    }
}

$slots_atuais = $DB->count_records('quiz_slots', ['quizid' => $quiz->id]);
if ($slots_atuais < $alvo_questoes) {
    $modcontext = context_module::instance($cm->id);
    // Moodle 5.x exige CONTEXT_MODULE e aceita $createifnotexists=true; 4.5 usa question_make_default_categories.
    $categoria = question_get_default_category($modcontext->id, true);
    if (!$categoria && function_exists('question_make_default_categories')) {
        $categoria = question_make_default_categories([$modcontext]);
    }
    $qtype = question_bank::get_qtype('multichoice');
    for ($i = $slots_atuais + 1; $i <= $alvo_questoes; $i++) {
        $questao = (object) ['qtype' => 'multichoice'];
        $form = (object) [
            'category' => "{$categoria->id},{$modcontext->id}",
            'name' => "Questao {$i}",
            'questiontext' => ['text' => "<p>Questão sintética {$i} do experimento Lab05.</p>", 'format' => FORMAT_HTML],
            'generalfeedback' => ['text' => '', 'format' => FORMAT_HTML],
            'defaultmark' => 1,
            'penalty' => 0,
            'single' => 1,
            'shuffleanswers' => 0,
            'answernumbering' => 'abc',
            'showstandardinstruction' => 0,
            'correctfeedback' => ['text' => '', 'format' => FORMAT_HTML],
            'partiallycorrectfeedback' => ['text' => '', 'format' => FORMAT_HTML],
            'incorrectfeedback' => ['text' => '', 'format' => FORMAT_HTML],
            'answer' => [
                ['text' => 'Alternativa A', 'format' => FORMAT_HTML],
                ['text' => 'Alternativa B', 'format' => FORMAT_HTML],
                ['text' => 'Alternativa C', 'format' => FORMAT_HTML],
                ['text' => 'Alternativa D', 'format' => FORMAT_HTML],
            ],
            'fraction' => [1.0, 0.0, 0.0, 0.0],
            'feedback' => array_fill(0, 4, ['text' => '', 'format' => FORMAT_HTML]),
        ];
        $salva = $qtype->save_question($questao, $form);
        quiz_add_quiz_question($salva->id, $quiz, 1, 1.0);
    }
}

$soma_slots = (float) $DB->get_field_sql(
    'SELECT COALESCE(SUM(maxmark), 0) FROM {quiz_slots} WHERE quizid = ?',
    [$quiz->id]
);
if (abs((float) $quiz->sumgrades - $soma_slots) > 0.0001) {
    \mod_quiz\quiz_settings::create($quiz->id)->get_grade_calculator()->recompute_quiz_sumgrades();
}
$transaction->allow_commit();

$total_questoes = $DB->count_records('quiz_slots', ['quizid' => $quiz->id]);
echo "curso_id={$curso->id} quiz_cmid={$cm->id} questoes={$total_questoes}\n";
