<?php
// Cria o estudante sintético e o quiz piloto (sem questões) no curso "lab05"; idempotente.
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
    ];
    create_module($info);
}

$cm = get_coursemodule_from_instance('quiz', $DB->get_field('quiz', 'id', ['course' => $curso->id]));
echo "curso_id={$curso->id} quiz_cmid={$cm->id}\n";
