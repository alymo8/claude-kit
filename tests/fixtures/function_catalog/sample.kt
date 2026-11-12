fun String.shout(): String = uppercase()

class Greeter {
    suspend fun greet(name: String): String {
        return name
    }

    private fun _internal() {}
}

internal fun <T> List<T>.second(): T = this[1]
